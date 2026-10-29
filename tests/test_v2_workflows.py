from django.test import TestCase
from django.core.exceptions import PermissionDenied
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintTransfer
from apps.accounts.models import User
from apps.workflows.services import WorkflowEngine
from apps.workflows.exceptions import WorkflowTransitionError, UnauthorizedWorkflowActionError
from apps.audit.models import AuditEvent

class WorkflowsV2TestCase(TestCase):
    def setUp(self):
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-WF-101',
            name='Workflow Engineering College',
            region='WESTERN',
            state='Maharashtra',
            district='Mumbai'
        )
        self.cat = ComplaintCategory.objects.create(code='WF_CAT', name='Administrative')

        self.rb_head = User.objects.create_user('rbh_wf', 'rbh@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_rb)
        self.pgrc_head = User.objects.create_user('pgrch_wf', 'pgrch@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_pgrc)
        self.rb_officer = User.objects.create_user('rbo_wf', 'rbo@example.com', 'Pass@123', role=User.Role.CASE_OFFICER, assigned_bureau=self.bureau_rb)
        self.pgrc_officer = User.objects.create_user('pgrco_wf', 'pgrco@example.com', 'Pass@123', role=User.Role.CASE_OFFICER, assigned_bureau=self.bureau_pgrc)

        self.complaint = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-WF01',
            institution=self.inst,
            title='Staff Irregularity Case',
            description='Investigation into faculty payroll irregularities.',
            category=self.cat,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.PENDING
        )

    def test_wf01_unauthorized_transfer_rejected(self):
        """WF01: Case officer from another bureau cannot request transfer of this complaint."""
        with self.assertRaises(UnauthorizedWorkflowActionError):
            WorkflowEngine.request_transfer(
                complaint=self.complaint,
                destination_bureau=self.bureau_pgrc,
                actor=self.pgrc_officer,
                reason="Unauthorized transfer attempt"
            )

    def test_wf02_invalid_status_transition_rejected(self):
        """WF02: Transitioning directly from PENDING to DISPOSED is blocked by state machine."""
        with self.assertRaises(WorkflowTransitionError):
            WorkflowEngine.transition_status(
                complaint=self.complaint,
                new_status=Complaint.Status.DISPOSED,
                actor=self.rb_head,
                remarks="Premature disposal attempt"
            )

    def test_wf03_audit_trail_completeness(self):
        """WF03: Every workflow mutation produces an immutable AuditEvent record."""
        # Valid assignment: PENDING -> UNDER_PROCESS
        WorkflowEngine.assign_officer(
            complaint=self.complaint,
            officer=self.rb_officer,
            actor=self.rb_head,
            remarks="Assigned to senior officer."
        )

        audit_entry = AuditEvent.objects.filter(
            entity_id=str(self.complaint.id),
            event_type="OFFICER_ASSIGNED"
        ).first()

        self.assertIsNotNone(audit_entry, "Audit record must be created for officer assignment!")
        self.assertEqual(audit_entry.actor_username, self.rb_head.username)

    def test_wf04_transfer_approval_and_rejection_correctness(self):
        """WF04: Transfer requires approval from destination bureau head and updates handling bureau."""
        # Move to UNDER_PROCESS first
        self.complaint.current_status = Complaint.Status.UNDER_PROCESS
        self.complaint.save()

        # Request transfer
        transfer = WorkflowEngine.request_transfer(
            complaint=self.complaint,
            destination_bureau=self.bureau_pgrc,
            actor=self.rb_head,
            reason="Jurisdiction belongs to PGRC"
        )
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.current_status, Complaint.Status.TRANSFERRED)

        # RB Head cannot approve transfer to PGRC (only PGRC Head can accept)
        with self.assertRaises(UnauthorizedWorkflowActionError):
            WorkflowEngine.approve_transfer(transfer, actor=self.rb_head, remarks="Self approval")

        # PGRC Head approves
        WorkflowEngine.approve_transfer(transfer, actor=self.pgrc_head, remarks="Accepted by PGRC")
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.currently_assigned_bureau, self.bureau_pgrc)
        self.assertEqual(self.complaint.current_status, Complaint.Status.UNDER_PROCESS)
