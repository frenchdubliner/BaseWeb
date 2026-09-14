from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import SingletonModel

DEFAULT_CONVENTION_NAME = "PAXE2026"


class ConventionSettings(SingletonModel):
    """
    Single global convention name shown/used across the app. Starts as
    DEFAULT_CONVENTION_NAME until an admin changes it - there is exactly
    one row (see SingletonModel), created on first access.
    """

    name = models.CharField(_("convention name"), max_length=100, default=DEFAULT_CONVENTION_NAME)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Convention settings"
        verbose_name_plural = "Convention settings"

    def __str__(self):
        return self.name
