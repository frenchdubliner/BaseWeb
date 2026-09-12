from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.encryption import EncryptedCharField


class DropoffLocation(models.TextChoices):
    ABINGTON = "abington", _("Abington")
    NORTON = "norton", _("Norton")
    SAUGUS = "saugus", _("Saugus")
    FRAMINGHAM = "framingham", _("Framingham")


class PaymentPreference(models.TextChoices):
    STORE_CREDIT_70 = "store_credit_70", _("70% of sale value in store credit")
    CASH_40 = "cash_40", _("40% of sale value in cash")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    phone_number = EncryptedCharField(_("phone number"), max_length=512)
    dropoff_location = models.CharField(
        _("dropoff location"), max_length=32, choices=DropoffLocation.choices
    )
    payment_preference = models.CharField(
        _("payment preference"), max_length=32, choices=PaymentPreference.choices
    )

    is_active = models.BooleanField(
        _("active"),
        default=False,
        help_text=_("Designates whether this user has verified their email address."),
    )
    is_staff = models.BooleanField(_("staff status"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    # MFA readiness (not enforced yet - see apps.accounts.models.MFAMethod)
    mfa_enabled = models.BooleanField(_("MFA enabled"), default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone_number", "dropoff_location", "payment_preference"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


class MFAMethodType(models.TextChoices):
    EMAIL_OTP = "email_otp", _("Email OTP")
    TOTP = "totp", _("Authenticator App (TOTP)")


class MFAMethod(models.Model):
    """
    Forward-looking model so multi-factor authentication (email OTP, TOTP /
    Google Authenticator / Microsoft Authenticator) can be enabled later
    without any schema redesign. Not enforced by the authentication flow yet.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mfa_methods")
    method_type = models.CharField(max_length=20, choices=MFAMethodType.choices)
    secret = EncryptedCharField(max_length=512, blank=True, null=True)
    is_enabled = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "method_type")

    def __str__(self):
        return f"{self.user.email} - {self.get_method_type_display()}"
