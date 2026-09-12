from django.contrib import admin

from .models import (
    AdminAllowedIP,
    AdminSecuritySettings,
    GeoRestrictionCountry,
    GeoRestrictionSettings,
    IPRestrictionEntry,
    IPRestrictionSettings,
    RegistrationAllowedCountry,
    RegistrationCountryRestriction,
)


class GeoRestrictionCountryInline(admin.TabularInline):
    model = GeoRestrictionCountry
    extra = 1


@admin.register(GeoRestrictionSettings)
class GeoRestrictionSettingsAdmin(admin.ModelAdmin):
    list_display = ("mode", "updated_at")
    inlines = [GeoRestrictionCountryInline]

    def has_add_permission(self, request):
        return not GeoRestrictionSettings.objects.exists()


class IPRestrictionEntryInline(admin.TabularInline):
    model = IPRestrictionEntry
    extra = 1


@admin.register(IPRestrictionSettings)
class IPRestrictionSettingsAdmin(admin.ModelAdmin):
    list_display = ("mode", "updated_at")
    inlines = [IPRestrictionEntryInline]

    def has_add_permission(self, request):
        return not IPRestrictionSettings.objects.exists()


class RegistrationAllowedCountryInline(admin.TabularInline):
    model = RegistrationAllowedCountry
    extra = 1


@admin.register(RegistrationCountryRestriction)
class RegistrationCountryRestrictionAdmin(admin.ModelAdmin):
    list_display = ("enabled", "updated_at")
    inlines = [RegistrationAllowedCountryInline]

    def has_add_permission(self, request):
        return not RegistrationCountryRestriction.objects.exists()


class AdminAllowedIPInline(admin.TabularInline):
    model = AdminAllowedIP
    extra = 1


@admin.register(AdminSecuritySettings)
class AdminSecuritySettingsAdmin(admin.ModelAdmin):
    list_display = ("ip_whitelist_enabled", "session_timeout_minutes")
    inlines = [AdminAllowedIPInline]

    def has_add_permission(self, request):
        return not AdminSecuritySettings.objects.exists()
