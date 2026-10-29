"""
Centralized Queryset Scoping Service for AUGIS V2
Ensures all list views, search queries, dashboard KPIs, and report exports
consistently respect authenticated user role and organizational boundaries.
"""

from django.db.models import Q
from apps.accounts.models import User
from apps.complaints.models import Complaint
from apps.coordination.models import CoordinationRecord
from apps.intelligence.models import OverlapCandidate
from apps.institutions.models import Institution
from apps.audit.models import AuditEvent

def get_scoped_complaints(user, base_qs=None):
    """
    Returns complaints accessible to the authenticated user.
    """
    if base_qs is None:
        qs = Complaint.objects.select_related(
            'institution', 'category', 'currently_assigned_bureau', 'currently_assigned_officer'
        ).all()
    else:
        qs = base_qs

    if not user or not user.is_authenticated:
        return qs.none()

    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
        return qs

    if user.role == User.Role.BUREAU_HEAD:
        return qs.filter(
            Q(currently_assigned_bureau=user.assigned_bureau) |
            Q(is_email_verified=True)
        )

    if user.role == User.Role.CASE_OFFICER:
        return qs.filter(
            Q(currently_assigned_bureau=user.assigned_bureau) |
            Q(currently_assigned_officer=user) |
            Q(is_email_verified=True)
        )

    if user.role == User.Role.REGIONAL_OFFICER:
        if user.authorized_region:
            return qs.filter(
                Q(institution__region=user.authorized_region) |
                Q(is_email_verified=True)
            )
        return qs.filter(is_email_verified=True)

    return qs.none()

def get_scoped_coordinations(user, base_qs=None):
    """
    Returns coordination records accessible to the authenticated user.
    """
    if base_qs is None:
        qs = CoordinationRecord.objects.select_related(
            'coordinating_bureau', 'created_by'
        ).prefetch_related(
            'participating_bureaus', 'related_complaints', 'responsible_officers'
        ).all()
    else:
        qs = base_qs

    if not user or not user.is_authenticated:
        return qs.none()

    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
        return qs

    if user.role == User.Role.BUREAU_HEAD:
        return qs.filter(
            Q(coordinating_bureau=user.assigned_bureau) |
            Q(participating_bureaus=user.assigned_bureau)
        ).distinct()

    if user.role == User.Role.CASE_OFFICER:
        return qs.filter(
            Q(responsible_officers=user) |
            Q(related_complaints__currently_assigned_officer=user)
        ).distinct()

    if user.role == User.Role.REGIONAL_OFFICER:
        if not user.authorized_region:
            return qs.none()
        return qs.filter(related_complaints__institution__region=user.authorized_region).distinct()

    return qs.none()

def get_scoped_overlap_candidates(user, base_qs=None):
    """
    Returns overlap candidates where the user has clearance to view at least one complaint.
    """
    if base_qs is None:
        qs = OverlapCandidate.objects.select_related(
            'first_complaint__institution',
            'first_complaint__currently_assigned_bureau',
            'first_complaint__category',
            'second_complaint__institution',
            'second_complaint__currently_assigned_bureau',
            'second_complaint__category',
            'reviewed_by'
        ).all()
    else:
        qs = base_qs

    if not user or not user.is_authenticated:
        return qs.none()

    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
        return qs

    if user.role == User.Role.BUREAU_HEAD:
        return qs.filter(
            Q(first_complaint__currently_assigned_bureau=user.assigned_bureau) |
            Q(second_complaint__currently_assigned_bureau=user.assigned_bureau)
        ).distinct()

    if user.role == User.Role.CASE_OFFICER:
        return qs.filter(
            Q(first_complaint__currently_assigned_bureau=user.assigned_bureau) |
            Q(second_complaint__currently_assigned_bureau=user.assigned_bureau) |
            Q(first_complaint__currently_assigned_officer=user) |
            Q(second_complaint__currently_assigned_officer=user)
        ).distinct()

    if user.role == User.Role.REGIONAL_OFFICER:
        if not user.authorized_region:
            return qs.none()
        return qs.filter(
            Q(first_complaint__institution__region=user.authorized_region) |
            Q(second_complaint__institution__region=user.authorized_region)
        ).distinct()

    return qs.none()

def get_scoped_institutions(user, base_qs=None):
    """
    Returns institutions scoped by regional jurisdiction if applicable.
    """
    if base_qs is None:
        qs = Institution.objects.all()
    else:
        qs = base_qs

    if not user or not user.is_authenticated:
        return qs.none()

    if user.role == User.Role.REGIONAL_OFFICER and user.authorized_region:
        return qs.filter(region=user.authorized_region)

    return qs

def get_scoped_audit_events(user, base_qs=None):
    """
    Only Super Admins or Senior Management can inspect global audit logs.
    """
    if base_qs is None:
        qs = AuditEvent.objects.all()
    else:
        qs = base_qs

    if not user or not user.is_authenticated:
        return qs.none()

    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT]:
        return qs

    return qs.none()
