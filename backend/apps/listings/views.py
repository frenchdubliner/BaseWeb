import csv

from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsVerified
from apps.audit.models import AuditLog
from apps.convention.models import ConventionSettings
from apps.security.utils import get_client_ip

from .csv_import import MAX_ROWS, TEMPLATE_CSV, normalize_row, parse_csv_file
from .models import GameListing
from .pdf import MAX_PRINT_ALL, generate_price_tag_pdf, generate_price_tags_pdf
from .serializers import AdminGameListingSerializer, GameListingSerializer


class GameListingViewSet(viewsets.ModelViewSet):
    """
    CRUD for a user's own game listings. Users can only ever see, edit or
    delete their own listings - the queryset is always scoped to the
    authenticated user, so another user's listing simply does not exist as
    far as this endpoint is concerned (404, not 403).
    """

    serializer_class = GameListingSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def get_queryset(self):
        return GameListing.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        # Message deliberately doesn't say *why* - the `printed` attribute
        # itself stays admin-only and is never named to the owner.
        if serializer.instance.printed:
            raise PermissionDenied("This listing can no longer be edited.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.printed:
            raise PermissionDenied("This listing can no longer be deleted.")
        instance.delete()


class GameListingCSVTemplateView(APIView):
    """Downloadable example CSV showing every column and accepted value."""

    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request):
        response = HttpResponse(TEMPLATE_CSV, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="game_listings_template.csv"'
        return response


class GameListingBulkUploadView(APIView):
    """
    Bulk-creates listings from an uploaded CSV. Best-effort: valid rows are
    imported even if other rows in the same file fail validation, and every
    failure is reported with its row number and field errors so the user
    can fix just those rows and re-upload.
    """

    permission_classes = [IsAuthenticated, IsVerified]
    parser_classes = [MultiPartParser]
    throttle_scope = "listings-bulk-upload"

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded. Use the 'file' field."}, status=400)
        if not file_obj.name.lower().endswith(".csv"):
            return Response({"detail": "File must be a .csv file."}, status=400)

        try:
            rows = parse_csv_file(file_obj)
        except (UnicodeDecodeError, csv.Error):
            return Response({"detail": "Could not read that file as CSV."}, status=400)

        if not rows:
            return Response({"detail": "The CSV file has no data rows."}, status=400)
        if len(rows) > MAX_ROWS:
            return Response(
                {"detail": f"Too many rows ({len(rows)}). Maximum {MAX_ROWS} rows per upload."},
                status=400,
            )

        created_listings = []
        row_errors = []
        for index, raw_row in enumerate(rows, start=1):
            data = normalize_row(raw_row)
            serializer = GameListingSerializer(data=data)
            if serializer.is_valid():
                listing = serializer.save(owner=request.user)
                created_listings.append(listing)
            else:
                row_errors.append(
                    {
                        "row": index,
                        "game_name": raw_row.get("game_name", ""),
                        "errors": serializer.errors,
                    }
                )

        return Response(
            {
                "created_count": len(created_listings),
                "error_count": len(row_errors),
                "errors": row_errors,
                "listings": GameListingSerializer(created_listings, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminGameListingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Admin-only view across every user's listings, with edit and delete.
    Creation is intentionally not supported here - listings are created by
    their owner (via the form or CSV import), never on their behalf.
    """

    serializer_class = AdminGameListingSerializer
    permission_classes = [IsAdminUser]
    queryset = GameListing.objects.select_related("owner").order_by("-created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        game_id = params.get("id")
        email = params.get("email")
        first_name = params.get("first_name")
        last_name = params.get("last_name")
        dropoff_location = params.get("dropoff_location")
        printed = params.get("printed")

        if game_id:
            try:
                qs = qs.filter(id=int(game_id))
            except ValueError:
                qs = qs.none()
        if email:
            qs = qs.filter(owner__email__icontains=email)
        if first_name:
            qs = qs.filter(owner__first_name__icontains=first_name)
        if last_name:
            qs = qs.filter(owner__last_name__icontains=last_name)
        if dropoff_location:
            qs = qs.filter(owner__dropoff_location__icontains=dropoff_location)
        if printed is not None and printed != "":
            qs = qs.filter(printed=printed.lower() in ("true", "1", "yes"))
        return qs

    def perform_update(self, serializer):
        listing = serializer.save()
        AuditLog.objects.create(
            event_type=AuditLog.EventType.ADMIN_ACTION,
            actor=self.request.user,
            target_user=listing.owner,
            ip_address=get_client_ip(self.request),
            metadata={
                "action": "listing_updated_via_admin_panel",
                "listing_id": listing.id,
                "game_name": listing.game_name,
            },
        )

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            event_type=AuditLog.EventType.ADMIN_ACTION,
            actor=self.request.user,
            target_user=instance.owner,
            ip_address=get_client_ip(self.request),
            metadata={
                "action": "listing_deleted_via_admin_panel",
                "listing_id": instance.id,
                "game_name": instance.game_name,
            },
        )
        instance.delete()

    @action(detail=True, methods=["get"], url_path="print", url_name="print")
    def print_tag(self, request, pk=None):
        """Downloads a 2in x 3in price tag PDF for this listing, and marks
        it as printed - after which only an admin can edit or delete it."""
        listing = self.get_object()
        convention_name = ConventionSettings.load().name
        pdf_bytes = generate_price_tag_pdf(listing, convention_name)

        if not listing.printed:
            listing.printed = True
            listing.save(update_fields=["printed"])
            AuditLog.objects.create(
                event_type=AuditLog.EventType.ADMIN_ACTION,
                actor=request.user,
                target_user=listing.owner,
                ip_address=get_client_ip(request),
                metadata={
                    "action": "listing_printed_via_admin_panel",
                    "listing_id": listing.id,
                    "game_name": listing.game_name,
                },
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="game-{listing.id}-price-tag.pdf"'
        return response

    @action(detail=False, methods=["get"], url_path="print-all", url_name="print-all")
    def print_all(self, request):
        """
        Downloads a single multi-page PDF - one page per listing - for
        every listing matching the currently applied filters (same query
        params as the list endpoint).
        """
        listings = list(self.get_queryset())
        if not listings:
            return Response({"detail": "No games match these filters."}, status=400)
        if len(listings) > MAX_PRINT_ALL:
            return Response(
                {"detail": f"Too many games ({len(listings)}). Narrow your filters to {MAX_PRINT_ALL} or fewer."},
                status=400,
            )

        convention_name = ConventionSettings.load().name
        pdf_bytes = generate_price_tags_pdf(listings, convention_name)

        unprinted_ids = [listing.id for listing in listings if not listing.printed]
        if unprinted_ids:
            GameListing.objects.filter(id__in=unprinted_ids).update(printed=True)
            AuditLog.objects.create(
                event_type=AuditLog.EventType.ADMIN_ACTION,
                actor=request.user,
                ip_address=get_client_ip(request),
                metadata={
                    "action": "listings_printed_via_admin_panel",
                    "listing_ids": unprinted_ids,
                },
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="price-tags.pdf"'
        return response
