import csv

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsVerified

from .csv_import import MAX_ROWS, TEMPLATE_CSV, normalize_row, parse_csv_file
from .models import GameListing
from .serializers import GameListingSerializer


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
