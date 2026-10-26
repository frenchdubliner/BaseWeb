from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler as default_exception_handler

from apps.security.utils import get_client_ip


def audit_logging_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to additionally log a 429
    (rate limit exceeded) to AuditLog - visible in the admin panel under
    Audit > Audit logs, filterable by event type.

    DRF's throttling rejects a request in APIView.initial(), before the
    view method itself ever runs, so none of the view-level audit logging
    elsewhere in this codebase (e.g. LoginAudit) ever sees these - the
    throttle counters also live in an in-memory cache (config/settings.py
    CACHES), not the database, so without this there is no record of a
    rate-limit event anywhere, even though the 429 response is real.
    """
    response = default_exception_handler(exc, context)

    if isinstance(exc, Throttled):
        from apps.audit.models import AuditLog

        request = context.get("request")
        view = context.get("view")
        AuditLog.objects.create(
            event_type=AuditLog.EventType.RATE_LIMIT_EXCEEDED,
            ip_address=get_client_ip(request) if request else None,
            metadata={
                "path": request.path if request else "",
                "method": request.method if request else "",
                "throttle_scope": getattr(view, "throttle_scope", ""),
                "wait_seconds": exc.wait,
            },
        )

    return response
