from django.db import transaction
from django.utils import timezone
from apps.complaints.models import (
    Complaint, ComplaintAction, ComplaintTransfer, ComplaintEscalation
)
from apps.audit.services import log_audit_event
from .exceptions import WorkflowTransitionError, UnauthorizedWorkflowActionError

# Permitted state transition map
PERMITTED_TRANSITIONS = {
    Complaint.Status.PENDING: {
        Complaint.Status.UNDER_PROCESS,
    },
    Complaint.Status.UNDER_PROCESS: {
        Complaint.Status.TRANSFERRED,
        Complaint.Status.ESCALATED,
        Complaint.Status.DISPOSED,
    },
    Complaint.Status.TRANSFERRED: {
        Complaint.Status.UNDER_PROCESS,
    },
    Complaint.Status.ESCALATED: {
        Complaint.Status.UNDER_PROCESS,
        Complaint.Status.DISPOSED,
    },
    Complaint.Status.DISPOSED: set(),  # Terminal state
}

class WorkflowEngine:
    @staticmethod
    def transition_status(complaint, new_status, actor, remarks='', request=None, next_action_required=None):
        """
        Executes a validated atomic status transition on a complaint.
        """
        old_status = complaint.current_status
        allowed_next = PERMITTED_TRANSITIONS.get(old_status, set())

        if new_status not in allowed_next:
            raise WorkflowTransitionError(
                f"Invalid transition from '{old_status}' to '{new_status}'. Allowed transitions: {', '.join(allowed_next) or 'None (Terminal)'}"
            )

        if not remarks or not remarks.strip():
            raise WorkflowTransitionError("Action remarks are mandatory for every status transition.")

        # Role authorization checks
        if new_status == Complaint.Status.DISPOSED:
            # Only Bureau Head, Super Admin, or Competent Authority (if escalated) can dispose
            if old_status == Complaint.Status.ESCALATED:
                if not (actor.is_superuser or actor.role in ['COMPETENT_AUTH', 'SUPER_ADMIN']):
                    raise UnauthorizedWorkflowActionError("Only Competent Authority or Super Admin can dispose an escalated complaint.")
            else:
                if not (actor.is_superuser or actor.role in ['BUREAU_HEAD', 'SUPER_ADMIN']):
                    raise UnauthorizedWorkflowActionError("Only Bureau Head or Super Admin is authorized to formally dispose a complaint.")

        with transaction.atomic():
            complaint.current_status = new_status
            if next_action_required is not None:
                complaint.next_action_required = next_action_required.strip()
            if new_status == Complaint.Status.DISPOSED:
                complaint.disposed_at = timezone.now()
                complaint.closure_remarks = remarks
                if not next_action_required:
                    complaint.next_action_required = 'None - Case Formally Disposed'
            complaint.save()

            # Record ComplaintAction history
            ComplaintAction.objects.create(
                complaint=complaint,
                action_type=ComplaintAction.ActionType.STATUS_CHANGE,
                previous_status=old_status,
                new_status=new_status,
                responsible_officer=actor,
                responsible_bureau=complaint.currently_assigned_bureau,
                remarks=remarks
            )

            # Record immutable audit event
            log_audit_event(
                actor=actor,
                event_type="WORKFLOW_TRANSITION",
                entity_name="Complaint",
                entity_id=str(complaint.id),
                change_summary={
                    "complaint_no": complaint.complaint_no,
                    "previous_status": old_status,
                    "new_status": new_status,
                    "remarks": remarks
                },
                request=request
            )

        return complaint

    @staticmethod
    def assign_officer(complaint, officer, actor, remarks='', request=None):
        """
        Assigns or reassigns an officer to a complaint.
        Moves PENDING to UNDER_PROCESS automatically if initially assigned.
        """
        if not (actor.is_superuser or actor.role in ['BUREAU_HEAD', 'SUPER_ADMIN']):
            raise UnauthorizedWorkflowActionError("Only Bureau Heads or Super Administrators can assign officers.")

        with transaction.atomic():
            prev_officer = complaint.currently_assigned_officer
            complaint.currently_assigned_officer = officer

            # If pending, auto-advance to UNDER_PROCESS
            prev_status = complaint.current_status
            if complaint.current_status == Complaint.Status.PENDING:
                complaint.current_status = Complaint.Status.UNDER_PROCESS

            complaint.save()

            action_type = (
                ComplaintAction.ActionType.REASSIGNED if prev_officer else ComplaintAction.ActionType.ASSIGNED
            )

            officer_name = officer.display_name if officer else "Unassigned"
            note = f"Assigned to {officer_name}. {remarks}".strip()

            ComplaintAction.objects.create(
                complaint=complaint,
                action_type=action_type,
                previous_status=prev_status,
                new_status=complaint.current_status,
                responsible_officer=actor,
                responsible_bureau=complaint.currently_assigned_bureau,
                remarks=note
            )

            log_audit_event(
                actor=actor,
                event_type="OFFICER_ASSIGNED",
                entity_name="Complaint",
                entity_id=str(complaint.id),
                change_summary={
                    "complaint_no": complaint.complaint_no,
                    "assigned_to": officer.username if officer else "None",
                    "previous_officer": prev_officer.username if prev_officer else "None"
                },
                request=request
            )

        return complaint

    @staticmethod
    def request_transfer(complaint, destination_bureau, actor, reason, request=None):
        """
        Initiates an inter-bureau transfer request.
        """
        from apps.accounts.access_policy import user_can_request_transfer
        if not user_can_request_transfer(actor, complaint):
            raise UnauthorizedWorkflowActionError("User is not authorized to request a transfer for this complaint.")

        if complaint.currently_assigned_bureau == destination_bureau:
            raise WorkflowTransitionError("Destination Bureau must differ from the current Bureau.")

        if not reason or not reason.strip():
            raise WorkflowTransitionError("Transfer reason is mandatory.")

        with transaction.atomic():
            transfer = ComplaintTransfer.objects.create(
                complaint=complaint,
                source_bureau=complaint.currently_assigned_bureau,
                destination_bureau=destination_bureau,
                requested_by=actor,
                reason=reason
            )

            # Move status to TRANSFERRED
            prev_status = complaint.current_status
            complaint.current_status = Complaint.Status.TRANSFERRED
            complaint.save()

            ComplaintAction.objects.create(
                complaint=complaint,
                action_type=ComplaintAction.ActionType.TRANSFER_REQUEST,
                previous_status=prev_status,
                new_status=Complaint.Status.TRANSFERRED,
                responsible_officer=actor,
                responsible_bureau=complaint.currently_assigned_bureau,
                remarks=f"Transfer requested to {destination_bureau.code}. Reason: {reason}"
            )

            log_audit_event(
                actor=actor,
                event_type="TRANSFER_REQUESTED",
                entity_name="ComplaintTransfer",
                entity_id=str(transfer.id),
                change_summary={
                    "complaint_no": complaint.complaint_no,
                    "source": complaint.currently_assigned_bureau.code,
                    "destination": destination_bureau.code,
                    "reason": reason
                },
                request=request
            )

        return transfer

    @staticmethod
    def approve_transfer(transfer=None, approver=None, decision_remarks='', new_officer=None, request=None, actor=None, remarks='', transfer_id=None):
        """
        Approves an inter-bureau transfer, updates complaint bureau, returns status to UNDER_PROCESS.
        Supports passing either transfer instance or transfer_id, and actor / remarks aliases.
        """
        target = transfer if transfer is not None else transfer_id
        approver = approver or actor
        decision_remarks = decision_remarks or remarks
        resolved_id = target.id if isinstance(target, ComplaintTransfer) else target

        with transaction.atomic():
            transfer_obj = ComplaintTransfer.objects.select_for_update().get(id=resolved_id)
            from apps.accounts.access_policy import user_can_approve_transfer
            if not user_can_approve_transfer(approver, transfer_obj):
                raise UnauthorizedWorkflowActionError("Only the destination Bureau Head or Super Admin can approve this transfer.")

            if transfer_obj.approval_status != ComplaintTransfer.Status.PENDING:
                raise WorkflowTransitionError("This transfer request has already been processed.")

            transfer_obj.approval_status = ComplaintTransfer.Status.APPROVED
            transfer_obj.approved_by = approver
            transfer_obj.decision_timestamp = timezone.now()
            transfer_obj.decision_remarks = decision_remarks
            transfer_obj.save()

            complaint = transfer_obj.complaint
            complaint.currently_assigned_bureau = transfer_obj.destination_bureau
            complaint.currently_assigned_officer = new_officer
            complaint.current_status = Complaint.Status.UNDER_PROCESS
            complaint.save()

            ComplaintAction.objects.create(
                complaint=complaint,
                action_type=ComplaintAction.ActionType.TRANSFER_APPROVED,
                previous_status=Complaint.Status.TRANSFERRED,
                new_status=Complaint.Status.UNDER_PROCESS,
                responsible_officer=approver,
                responsible_bureau=transfer_obj.destination_bureau,
                remarks=f"Transfer approved. Transferred to {transfer_obj.destination_bureau.code}. {decision_remarks}".strip()
            )

            log_audit_event(
                actor=approver,
                event_type="TRANSFER_APPROVED",
                entity_name="ComplaintTransfer",
                entity_id=str(transfer_obj.id),
                change_summary={
                    "complaint_no": complaint.complaint_no,
                    "destination": transfer_obj.destination_bureau.code,
                    "approver": approver.username
                },
                request=request
            )

        return transfer_obj

    @staticmethod
    def escalate_complaint(complaint, escalation_level, actor, reason, responsible_authority=None, request=None):
        """
        Escalates complaint to higher authority.
        """
        if not reason or not reason.strip():
            raise WorkflowTransitionError("Reason for escalation is mandatory.")

        with transaction.atomic():
            escalation = ComplaintEscalation.objects.create(
                complaint=complaint,
                escalation_level=escalation_level,
                reason=reason,
                responsible_authority=responsible_authority
            )

            prev_status = complaint.current_status
            complaint.current_status = Complaint.Status.ESCALATED
            complaint.save()

            ComplaintAction.objects.create(
                complaint=complaint,
                action_type=ComplaintAction.ActionType.ESCALATION,
                previous_status=prev_status,
                new_status=Complaint.Status.ESCALATED,
                responsible_officer=actor,
                responsible_bureau=complaint.currently_assigned_bureau,
                remarks=f"Escalated [{escalation_level}]. Reason: {reason}"
            )

            log_audit_event(
                actor=actor,
                event_type="COMPLAINT_ESCALATED",
                entity_name="ComplaintEscalation",
                entity_id=str(escalation.id),
                change_summary={
                    "complaint_no": complaint.complaint_no,
                    "level": escalation_level,
                    "reason": reason
                },
                request=request
            )

        return escalation
