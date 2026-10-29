"""
Centralized Object-Level Access Policy for AUGIS V2
Enforces strict role-based and object-level authorization across all domain resources:
Complaints, Coordination Workspaces, Overlap Candidates, Documents, and Reports.
"""

from apps.accounts.models import User

def user_can_view_complaint(user, complaint):
    """
    Object-level access boundary for viewing complaints:
    1. Super Admin, Senior Mgmt, Competent Authority: Global read access.
    2. Bureau Head: Complaints assigned to their designated Bureau.
    3. Case Officer: Complaints assigned to their designated Bureau or directly to them.
    4. Regional Officer: Complaints where the institution is within their authorized region.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
        return True
    if user.role == User.Role.BUREAU_HEAD:
        return complaint.currently_assigned_bureau_id == user.assigned_bureau_id
    if user.role == User.Role.CASE_OFFICER:
        return (
            complaint.currently_assigned_bureau_id == user.assigned_bureau_id or
            complaint.currently_assigned_officer_id == user.id
        )
    if user.role == User.Role.REGIONAL_OFFICER:
        if not user.authorized_region or not complaint.institution:
            return False
        return complaint.institution.region == user.authorized_region
    return False

def user_can_modify_complaint(user, complaint):
    """
    Mutation boundary for updating status or remarks on a complaint:
    - Super Admins: Global mutation.
    - Competent Authority: Escalated complaints.
    - Bureau Head: Complaints in their designated Bureau.
    - Case Officer: Only complaints directly assigned to them in their Bureau.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        return True
    if user.role == User.Role.COMPETENT_AUTH and complaint.current_status == 'ESCALATED':
        return True
    if user.role == User.Role.BUREAU_HEAD:
        return complaint.currently_assigned_bureau_id == user.assigned_bureau_id
    if user.role == User.Role.CASE_OFFICER:
        return (
            complaint.currently_assigned_bureau_id == user.assigned_bureau_id and
            complaint.currently_assigned_officer_id == user.id
        )
    return False

def user_can_assign_officer(user, complaint):
    """Only Bureau Heads of the handling Bureau or Super Admins can assign officers."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        return True
    if user.role == User.Role.BUREAU_HEAD:
        return complaint.currently_assigned_bureau_id == user.assigned_bureau_id
    return False

def user_can_request_transfer(user, complaint):
    """Case Officer assigned to the case or Bureau Head can request transfer."""
    return user_can_modify_complaint(user, complaint)

def user_can_approve_transfer(user, transfer):
    """
    Destination Bureau Head or Super Admin can approve/reject inter-bureau transfer.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        return True
    if user.role == User.Role.BUREAU_HEAD:
        return transfer.destination_bureau_id == user.assigned_bureau_id
    return False

def user_can_escalate_complaint(user, complaint):
    """Bureau Head, assigned Case Officer, or Super Admin can escalate."""
    return user_can_modify_complaint(user, complaint)

def user_can_resolve_escalation(user, complaint):
    """Only Competent Authority or Super Admin can resolve escalated complaints."""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.COMPETENT_AUTH]

def user_can_upload_document(user, complaint):
    """
    Explicit write/upload permission:
    Requires user to have modification authority on the case.
    Read-only access alone does NOT grant upload capability.
    """
    return user_can_modify_complaint(user, complaint)

def user_can_download_document(user, document):
    """
    Enforces document visibility classification rules:
    - PUBLIC_SUMMARY: Any user who can view the complaint can download.
    - INTERNAL_ONLY: Handled officers, Bureau Heads of the handling bureau, Super Admins.
    - CONFIDENTIAL: Only the assigned Case Officer, Handling Bureau Head, Competent Authority, Super Admin.
    """
    if not user or not user.is_authenticated:
        return False
    complaint = document.complaint
    if not user_can_view_complaint(user, complaint):
        return False

    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        return True

    classification = document.visibility_classification
    if classification == 'PUBLIC_SUMMARY':
        return True

    if classification == 'INTERNAL_ONLY':
        if user.role in [User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
            return True
        return complaint.currently_assigned_bureau_id == user.assigned_bureau_id

    if classification == 'CONFIDENTIAL':
        if user.role == User.Role.COMPETENT_AUTH and complaint.current_status == 'ESCALATED':
            return True
        if user.role == User.Role.BUREAU_HEAD:
            return complaint.currently_assigned_bureau_id == user.assigned_bureau_id
        if user.role == User.Role.CASE_OFFICER:
            return (
                complaint.currently_assigned_bureau_id == user.assigned_bureau_id and
                complaint.currently_assigned_officer_id == user.id
            )
        return False

    return False

def user_can_view_coordination(user, coordination):
    """
    Object-level access boundary for coordination rooms:
    - Super Admin, Senior Mgmt, Competent Authority: Full read access.
    - Bureau Head: Must be head of coordinating bureau or a participating bureau.
    - Case Officer: Must belong to coordinating/participating bureau AND be designated responsible officer or handling one of the related complaints.
    - Regional Officer: If any complaint in coordination belongs to their authorized region.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
        return True

    participating_ids = set(coordination.participating_bureaus.values_list('id', flat=True))
    if coordination.coordinating_bureau_id:
        participating_ids.add(coordination.coordinating_bureau_id)

    if user.role == User.Role.BUREAU_HEAD:
        return user.assigned_bureau_id in participating_ids

    if user.role == User.Role.CASE_OFFICER:
        if user.assigned_bureau_id not in participating_ids:
            return False
        # Officer must be designated responsible officer or assigned to one of the related complaints
        is_responsible = coordination.responsible_officers.filter(id=user.id).exists()
        is_assigned_to_complaint = coordination.related_complaints.filter(currently_assigned_officer=user).exists()
        return is_responsible or is_assigned_to_complaint

    if user.role == User.Role.REGIONAL_OFFICER:
        if not user.authorized_region:
            return False
        return coordination.related_complaints.filter(institution__region=user.authorized_region).exists()

    return False

def user_can_create_coordination(user):
    """Only Super Admin, Bureau Heads, or Competent Authority can establish joint coordination."""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.COMPETENT_AUTH]

def user_can_add_coordination_note(user, coordination):
    """
    Participating officers, Bureau Heads of participating bureaus, or Super Admins can post notes.
    """
    return user_can_view_coordination(user, coordination)

def user_can_update_coordination_status(user, coordination):
    """
    Only Lead Coordinating Bureau Head, Competent Authority, or Super Admin can transition coordination status.
    Unrelated Bureau Heads are strictly forbidden.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.COMPETENT_AUTH]:
        return True
    if user.role == User.Role.BUREAU_HEAD:
        return coordination.coordinating_bureau_id == user.assigned_bureau_id
    return False

def user_can_view_overlap_candidate(user, candidate):
    """
    Can view overlap candidate if authorized to view at least one of the complaints.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH]:
        return True
    return (
        user_can_view_complaint(user, candidate.first_complaint) or
        user_can_view_complaint(user, candidate.second_complaint)
    )

def user_can_review_overlap_candidate(user, candidate):
    """
    Only Bureau Heads of involved bureaus, Competent Authority, or Super Admin can confirm/dismiss candidates.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in [User.Role.SUPER_ADMIN, User.Role.COMPETENT_AUTH]:
        return True
    if user.role == User.Role.BUREAU_HEAD:
        involved_bureaus = {
            candidate.first_complaint.currently_assigned_bureau_id,
            candidate.second_complaint.currently_assigned_bureau_id
        }
        return user.assigned_bureau_id in involved_bureaus
    return False

def user_can_access_reports(user):
    """Authorized roles for analytics and reports exports."""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.role in [
        User.Role.SUPER_ADMIN,
        User.Role.SENIOR_MGMT,
        User.Role.COMPETENT_AUTH,
        User.Role.BUREAU_HEAD,
        User.Role.REGIONAL_OFFICER
    ]
