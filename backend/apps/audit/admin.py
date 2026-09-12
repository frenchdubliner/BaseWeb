from django.contrib import admin

from .models import AuditLog, LoginAudit


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "action", "email_attempted", "user", "ip_address", "country", "city")
    list_filter = ("action", "country")
    search_fields = ("email_attempted", "ip_address", "user__email")
    readonly_fields = [f.name for f in LoginAudit._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "event_type", "actor", "target_user", "ip_address")
    list_filter = ("event_type",)
    search_fields = ("actor__email", "target_user__email", "ip_address")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
