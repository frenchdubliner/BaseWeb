from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import MFAMethod, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "dropoff_location", "payment_preference")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "dropoff_location",
                    "payment_preference",
                )
            },
        ),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "mfa_enabled", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "dropoff_location",
                    "payment_preference",
                ),
            },
        ),
    )


@admin.register(MFAMethod)
class MFAMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "method_type", "is_enabled", "is_confirmed", "created_at")
    list_filter = ("method_type", "is_enabled")
    search_fields = ("user__email",)
