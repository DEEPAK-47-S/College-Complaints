from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from .access_policy import (
    user_can_view_complaint,
    user_can_modify_complaint,
    user_can_assign_officer,
    user_can_request_transfer,
    user_can_approve_transfer,
    user_can_escalate_complaint,
    user_can_resolve_escalation,
    user_can_upload_document,
    user_can_download_document,
    user_can_view_coordination,
    user_can_create_coordination,
    user_can_add_coordination_note,
    user_can_update_coordination_status,
    user_can_view_overlap_candidate,
    user_can_review_overlap_candidate,
    user_can_access_reports,
)

# Backward-compatible alias
user_can_access_complaint = user_can_view_complaint

def role_required(*allowed_roles):
    """
    Decorator requiring the authenticated user to hold one of the specified roles.
    Superusers automatically pass.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not possess the required role to access this resource.")
        return _wrapped_view
    return decorator
