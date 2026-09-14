from rest_framework import generics
from rest_framework.permissions import IsAdminUser

from apps.audit.models import AuditLog
from apps.security.utils import get_client_ip

from .models import ConventionSettings
from .serializers import ConventionSettingsSerializer


class ConventionSettingsView(generics.RetrieveUpdateAPIView):
    """
    Admin-only: view/create/update the single global convention name.
    There is always exactly one row (see SingletonModel) - created on
    first access with the default name if no admin has set one yet.
    """

    serializer_class = ConventionSettingsSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        return ConventionSettings.load()

    def perform_update(self, serializer):
        old_name = serializer.instance.name
        instance = serializer.save()
        if instance.name != old_name:
            AuditLog.objects.create(
                event_type=AuditLog.EventType.ADMIN_ACTION,
                actor=self.request.user,
                ip_address=get_client_ip(self.request),
                metadata={
                    "action": "convention_name_updated",
                    "old_name": old_name,
                    "new_name": instance.name,
                },
            )
