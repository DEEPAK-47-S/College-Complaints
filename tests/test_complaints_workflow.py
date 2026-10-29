import io
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintAction, ComplaintTransfer, ComplaintEscalation
from apps.complaints.services import create_complaint, generate_complaint_number, validate_and_save_document
from apps.workflows.services import WorkflowEngine
from apps.workflows.exceptions import WorkflowTransitionError, UnauthorizedWorkflowActionError

class ComplaintWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.rb_head = User.objects.create_user(
            username='rb_head_user',
            email='rbhead@test.gov.in',
            password='TestPassword@123',
            role=User.Role.BUREAU_HEAD,
            assigned_bureau=self.bureau_rb,
            display_name='RB Head'
        )

        self.pgrc_head = User.objects.create_user(
            username='pgrc_head_user',
            email='pgrchead@test.gov.in',
            password='TestPassword@123',
            role=User.Role.BUREAU_HEAD,
            assigned_bureau=self.bureau_pgrc,
            display_name='PGRC Head'
        )

        self.rb_officer = User.objects.create_user(
            username='rb_officer_u',
            email='rbofficer@test.gov.in',
            password='TestPassword@123',
            role=User.Role.CASE_OFFICER,
            assigned_bureau=self.bureau_rb,
            display_name='Officer Vikram'
        )

        self.competent_auth = User.objects.create_user(
            username='auth_user',
            email='auth@test.gov.in',
            password='TestPassword@123',
            role=User.Role.COMPETENT_AUTH,
            display_name='Chairman Authority'
        )

        self.institution = Institution.objects.create(
            aicte_permanent_id='1-AICTE-WORKFLOW',
            name='Workflow National Engineering College',
            institution_type='ENGINEERING',
            address='Highway 1',
            district='Pune',
            state='Maharashtra',
            region='WESTERN',
            pincode='411001'
        )

        self.category = ComplaintCategory.objects.create(
            code='INFRA',
            name='Infrastructure Deficiencies',
            default_sla_days=30
        )

    def test_t05_complaint_creation_persists_correctly(self):
        """T05: Complaint creation persists correctly with valid relationships and audit."""
        complaint = create_complaint(
            institution=self.institution,
            title='Inadequate Computer Lab Facilities',
            description='Only 10 functioning computers for 120 intake students in computer science.',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head,
            priority='HIGH'
        )

        self.assertIsNotNone(complaint.id)
        self.assertTrue(complaint.complaint_no.startswith('AICTE-'))
        self.assertEqual(complaint.current_status, Complaint.Status.PENDING)
        self.assertEqual(complaint.actions.count(), 1)
        self.assertEqual(complaint.actions.first().action_type, ComplaintAction.ActionType.CREATED)

    def test_t06_concurrent_complaint_creation_generates_unique_ids(self):
        """T06: Sequential / concurrent complaint creation generates unique sequential IDs."""
        id1 = generate_complaint_number('RB', 2026)
        c1 = Complaint.objects.create(
            complaint_no=id1,
            institution=self.institution,
            title='Test Concurrent 1',
            description='Desc 1',
            category=self.category,
            currently_assigned_bureau=self.bureau_rb
        )

        id2 = generate_complaint_number('RB', 2026)
        self.assertNotEqual(id1, id2)
        self.assertTrue(id2.endswith('00002') or int(id2.split('-')[-1]) > int(id1.split('-')[-1]))

    def test_t07_officer_assignment_updates_the_correct_case(self):
        """T07: Officer assignment updates the correct case and auto-advances PENDING to UNDER_PROCESS."""
        complaint = create_complaint(
            institution=self.institution,
            title='Faculty salary withholding',
            description='Faculty not paid for 3 months',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )

        WorkflowEngine.assign_officer(complaint, self.rb_officer, self.rb_head, 'Assigned for immediate scrutiny.')
        complaint.refresh_from_db()

        self.assertEqual(complaint.currently_assigned_officer, self.rb_officer)
        self.assertEqual(complaint.current_status, Complaint.Status.UNDER_PROCESS)
        self.assertTrue(complaint.actions.filter(action_type=ComplaintAction.ActionType.ASSIGNED).exists())

    def test_t08_invalid_workflow_transition_is_rejected(self):
        """T08: Invalid workflow transition (e.g. PENDING directly to DISPOSED) is rejected."""
        complaint = create_complaint(
            institution=self.institution,
            title='Unapproved extension',
            description='Running unapproved batches',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )

        with self.assertRaises(WorkflowTransitionError):
            WorkflowEngine.transition_status(
                complaint,
                Complaint.Status.DISPOSED,
                self.rb_head,
                'Attempting invalid immediate closure without scrutiny'
            )

    def test_t09_complaint_transfer_records_complete_history(self):
        """T09: Inter-bureau transfer records complete approval history and updates handling bureau."""
        complaint = create_complaint(
            institution=self.institution,
            title='Fee refund dispute',
            description='Student demanding capitation fee refund',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )
        # Advance to under process
        WorkflowEngine.assign_officer(complaint, self.rb_officer, self.rb_head, 'Initial assignment')

        transfer = WorkflowEngine.request_transfer(
            complaint=complaint,
            destination_bureau=self.bureau_pgrc,
            actor=self.rb_officer,
            reason='Capitation fees and student grievances belong to PGRC mandate.'
        )

        complaint.refresh_from_db()
        self.assertEqual(complaint.current_status, Complaint.Status.TRANSFERRED)

        # PGRC Head approves
        WorkflowEngine.approve_transfer(
            transfer_id=transfer.id,
            approver=self.pgrc_head,
            decision_remarks='Accepted by PGRC.'
        )

        complaint.refresh_from_db()
        self.assertEqual(complaint.currently_assigned_bureau, self.bureau_pgrc)
        self.assertEqual(complaint.current_status, Complaint.Status.UNDER_PROCESS)

    def test_t10_escalation_is_visible_and_resolvable_by_competent_authority(self):
        """T10: Escalation sets status to ESCALATED and is resolvable by Competent Authority."""
        complaint = create_complaint(
            institution=self.institution,
            title='Severe Impasse on Norms',
            description='Institution refuses to appear before scrutiny committee',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )
        WorkflowEngine.assign_officer(complaint, self.rb_officer, self.rb_head)

        escalation = WorkflowEngine.escalate_complaint(
            complaint=complaint,
            escalation_level=ComplaintEscalation.Level.LEVEL_3_CHAIRMAN,
            actor=self.rb_head,
            reason='Persistent refusal to furnish mandatory records.'
        )

        complaint.refresh_from_db()
        self.assertEqual(complaint.current_status, Complaint.Status.ESCALATED)

        # Competent Authority disposes
        WorkflowEngine.transition_status(
            complaint=complaint,
            new_status=Complaint.Status.DISPOSED,
            actor=self.competent_auth,
            remarks='Hearing conducted. Regulatory directions issued.'
        )

        complaint.refresh_from_db()
        self.assertEqual(complaint.current_status, Complaint.Status.DISPOSED)
        self.assertIsNotNone(complaint.disposed_at)

    def test_t19_unauthorized_officers_cannot_modify_other_bureau_records(self):
        """T19: Unauthorized officer cannot transition another bureau's complaints."""
        complaint = create_complaint(
            institution=self.institution,
            title='RB Proprietary Scrutiny',
            description='Under RB scrutiny only',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )

        # PGRC Head tries to transition RB complaint without authority
        self.client.login(username='pgrc_head_user', password='TestPassword@123')
        response = self.client.post(reverse('complaints:transition', args=[complaint.id]), {
            'new_status': 'UNDER_PROCESS',
            'remarks': 'Attempt unauthorized mutation'
        })
        self.assertEqual(response.status_code, 403)

    def test_t25_unauthorized_document_downloads_fail(self):
        """T25: Unauthorized officer cannot download restricted private files."""
        complaint = create_complaint(
            institution=self.institution,
            title='Confidential Evidence Case',
            description='Confidential file attached',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )

        file_content = b"%PDF-1.4 Mock confidential evidence document"
        uploaded_file = SimpleUploadedFile("evidence.pdf", file_content, content_type="application/pdf")
        doc = validate_and_save_document(complaint, uploaded_file, self.rb_head)

        # PGRC officer attempts to download RB document
        self.client.login(username='pgrc_head_user', password='TestPassword@123')
        response = self.client.get(reverse('complaints:download_document', args=[complaint.id, doc.id]))
        self.assertEqual(response.status_code, 403)

    def test_t26_invalid_file_uploads_are_rejected(self):
        """T26: Malicious or invalid extensions (.exe, .sh, .py) are rejected."""
        complaint = create_complaint(
            institution=self.institution,
            title='Malicious Upload Attempt',
            description='Test file extension defense',
            category=self.category,
            bureau=self.bureau_rb,
            source_channel='PORTAL',
            created_by=self.rb_head
        )

        bad_file = SimpleUploadedFile("malware.exe", b"binary content", content_type="application/x-msdownload")
        with self.assertRaises(ValidationError):
            validate_and_save_document(complaint, bad_file, self.rb_head)
