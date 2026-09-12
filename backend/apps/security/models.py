from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import SingletonModel


class RestrictionMode(models.TextChoices):
    DISABLED = "disabled", _("Disabled")
    WHITELIST = "whitelist", _("Whitelist (allow only listed)")
    BLACKLIST = "blacklist", _("Blacklist (block listed)")


# ---------------------------------------------------------------------------
# Site-wide geo restriction (applies to every request)
# ---------------------------------------------------------------------------
class GeoRestrictionSettings(SingletonModel):
    mode = models.CharField(max_length=16, choices=RestrictionMode.choices, default=RestrictionMode.DISABLED)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Geo restriction settings"
        verbose_name_plural = "Geo restriction settings"

    def __str__(self):
        return f"Geo restriction ({self.mode})"


class GeoRestrictionCountry(models.Model):
    settings = models.ForeignKey(GeoRestrictionSettings, on_delete=models.CASCADE, related_name="countries")
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2, e.g. US, CA")

    class Meta:
        unique_together = ("settings", "country_code")

    def __str__(self):
        return self.country_code


# ---------------------------------------------------------------------------
# Site-wide IP restriction (applies before authentication)
# ---------------------------------------------------------------------------
class IPRestrictionSettings(SingletonModel):
    mode = models.CharField(max_length=16, choices=RestrictionMode.choices, default=RestrictionMode.DISABLED)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "IP restriction settings"
        verbose_name_plural = "IP restriction settings"

    def __str__(self):
        return f"IP restriction ({self.mode})"


class IPRestrictionEntry(models.Model):
    settings = models.ForeignKey(IPRestrictionSettings, on_delete=models.CASCADE, related_name="entries")
    ip_or_cidr = models.CharField(max_length=64, help_text="e.g. 203.0.113.5 or 203.0.113.0/24")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("settings", "ip_or_cidr")

    def __str__(self):
        return self.ip_or_cidr


# ---------------------------------------------------------------------------
# Registration-only country restriction
# ---------------------------------------------------------------------------
class RegistrationCountryRestriction(SingletonModel):
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registration country restriction"
        verbose_name_plural = "Registration country restriction"

    def __str__(self):
        return f"Registration country restriction ({'enabled' if self.enabled else 'disabled'})"


class RegistrationAllowedCountry(models.Model):
    restriction = models.ForeignKey(
        RegistrationCountryRestriction, on_delete=models.CASCADE, related_name="allowed_countries"
    )
    country_code = models.CharField(max_length=2)

    class Meta:
        unique_together = ("restriction", "country_code")

    def __str__(self):
        return self.country_code


# ---------------------------------------------------------------------------
# Admin panel hardening
# ---------------------------------------------------------------------------
class AdminSecuritySettings(SingletonModel):
    ip_whitelist_enabled = models.BooleanField(default=False)
    session_timeout_minutes = models.PositiveIntegerField(default=15)

    class Meta:
        verbose_name = "Admin security settings"
        verbose_name_plural = "Admin security settings"

    def __str__(self):
        return "Admin security settings"


class AdminAllowedIP(models.Model):
    settings = models.ForeignKey(AdminSecuritySettings, on_delete=models.CASCADE, related_name="allowed_ips")
    ip_or_cidr = models.CharField(max_length=64)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("settings", "ip_or_cidr")

    def __str__(self):
        return self.ip_or_cidr
