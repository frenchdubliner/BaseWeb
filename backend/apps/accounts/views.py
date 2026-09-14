from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import exceptions, generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.models import AuditLog, LoginAudit
from apps.security.geoip import get_country_city
from apps.security.models import RegistrationCountryRestriction
from apps.security.utils import get_client_ip

from .emails import send_password_reset_email, send_verification_email
from .permissions import IsVerified
from .serializers import (
    AdminUserSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    UserProfileSerializer,
)
from .tokens import read_email_verification_token, read_password_reset_token

User = get_user_model()


def _geo(ip):
    if not settings.GEOIP_ENABLED:
        return "", ""
    country, city = get_country_city(ip)
    return country or "", city or ""


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        ip = get_client_ip(request)
        country, _city = _geo(ip)

        restriction = RegistrationCountryRestriction.objects.first()
        if restriction and restriction.enabled and country:
            allowed = set(restriction.allowed_countries.values_list("country_code", flat=True))
            if country not in allowed:
                AuditLog.objects.create(
                    event_type=AuditLog.EventType.REGISTRATION_ATTEMPT,
                    ip_address=ip,
                    metadata={
                        "email": request.data.get("email"),
                        "success": False,
                        "reason": "country_restricted",
                        "country": country,
                    },
                )
                return Response(
                    {"detail": "Registration is not currently available in your region."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except exceptions.ValidationError:
            AuditLog.objects.create(
                event_type=AuditLog.EventType.REGISTRATION_ATTEMPT,
                ip_address=ip,
                metadata={"email": request.data.get("email"), "success": False},
            )
            raise

        user = serializer.save()
        AuditLog.objects.create(
            event_type=AuditLog.EventType.REGISTRATION_ATTEMPT,
            actor=user,
            target_user=user,
            ip_address=ip,
            metadata={"email": user.email, "success": True},
        )
        send_verification_email(user)
        return Response(
            {"detail": "Registration successful. Please check your email to verify your account."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        ip = get_client_ip(request)
        country, city = _geo(ip)
        LoginAudit.objects.create(
            user=user,
            email_attempted=user.email,
            action=LoginAudit.Action.LOGIN_SUCCESS,
            ip_address=ip,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
            country=country,
            city=city,
        )
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        try:
            if refresh_token:
                RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass

        LoginAudit.objects.create(
            user=request.user,
            email_attempted=request.user.email,
            action=LoginAudit.Action.LOGOUT,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
        )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "")
        data = read_email_verification_token(token)
        if not data:
            return Response({"detail": "Invalid or expired verification link."}, status=400)

        try:
            user = User.objects.get(pk=data["uid"], email=data["email"])
        except User.DoesNotExist:
            return Response({"detail": "Invalid verification link."}, status=400)

        if user.is_active:
            return Response({"detail": "Email already verified."}, status=200)

        user.is_active = True
        user.save(update_fields=["is_active"])
        AuditLog.objects.create(
            event_type=AuditLog.EventType.ACCOUNT_ACTIVATION,
            actor=user,
            target_user=user,
            ip_address=get_client_ip(request),
        )
        return Response({"detail": "Email verified successfully. You can now log in."}, status=200)


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "resend-verification"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                send_verification_email(user)
        except User.DoesNotExist:
            pass

        return Response(
            {"detail": "If an account exists and is not yet verified, a new email has been sent."}
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password-reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()

        try:
            user = User.objects.get(email=email)
            send_password_reset_email(user)
        except User.DoesNotExist:
            pass

        return Response({"detail": "If an account exists, a password reset email has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password-reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        data = read_password_reset_token(serializer.validated_data["token"])
        if not data:
            return Response({"detail": "Invalid or expired reset link."}, status=400)

        try:
            user = User.objects.get(pk=data["uid"])
        except User.DoesNotExist:
            return Response({"detail": "Invalid reset link."}, status=400)

        if user.password[-16:] != data.get("pw"):
            return Response({"detail": "This reset link has already been used."}, status=400)

        validate_password(serializer.validated_data["new_password"], user=user)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        AuditLog.objects.create(
            event_type=AuditLog.EventType.PASSWORD_CHANGE,
            actor=user,
            target_user=user,
            ip_address=get_client_ip(request),
            metadata={"method": "reset"},
        )
        return Response({"detail": "Password has been reset successfully."})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        AuditLog.objects.create(
            event_type=AuditLog.EventType.PASSWORD_CHANGE,
            actor=user,
            target_user=user,
            ip_address=get_client_ip(request),
            metadata={"method": "change"},
        )
        return Response({"detail": "Password changed successfully."})


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Available before email verification (profile view), and to the owner
    only. Never publicly accessible.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserAdminDetailView(generics.RetrieveAPIView):
    """Administrator-only lookup of another user's profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    lookup_field = "pk"


class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Admin-only user directory: list every user (with filters) and edit
    their profile information. Deliberately does not support create or
    delete - accounts are created through registration, and role changes
    stay in the Django admin panel.
    """

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by("-date_joined")

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        email = params.get("email")
        first_name = params.get("first_name")
        last_name = params.get("last_name")

        if email:
            qs = qs.filter(email__icontains=email)
        if first_name:
            qs = qs.filter(first_name__icontains=first_name)
        if last_name:
            qs = qs.filter(last_name__icontains=last_name)
        return qs

    def list(self, request, *args, **kwargs):
        # phone_number is encrypted at rest (see apps.common.encryption), so
        # it cannot be filtered at the database level - filter in Python
        # after decryption instead.
        users = list(self.get_queryset())
        phone = request.query_params.get("phone_number")
        if phone:
            phone = phone.strip()
            users = [u for u in users if phone in (u.phone_number or "")]
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            event_type=AuditLog.EventType.ADMIN_ACTION,
            actor=self.request.user,
            target_user=instance,
            ip_address=get_client_ip(self.request),
            metadata={
                "action": "user_updated_via_admin_panel",
                "fields": list(self.request.data.keys()),
            },
        )
