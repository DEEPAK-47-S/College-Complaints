import os
import io
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import PermissionDenied, ValidationError, ImproperlyConfigured
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintDocument
from apps.coordination.models import CoordinationRecord, CoordinationNote
from apps.coordination.services import CoordinationService
from apps.intelligence.models import OverlapCandidate
from apps.complaints.services import validate_and_save_document

class SecurityV2TestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Bureaus
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')
        self.bureau_adv = Bureau.objects.create(code='ADV', name='Approval Bureau')

        # Users
        self.admin = User.objects.create_superuser('admin_sec', 'admin@example.com', 'Pass@123')
        self.rb_head = User.objects.create_user('rb_head_sec', 'rbh@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_rb)
        self.pgrc_head = User.objects.create_user('pgrc_head_sec', 'pgrch@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_pgrc)
        self.adv_head = User.objects.create_user('adv_head_sec', 'advh@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_adv)
        self.rb_officer = User.objects.create_user('rb_off_sec', 'rbo@example.com', 'Pass@123', role=User.Role.CASE_OFFICER, assigned_bureau=self.bureau_rb)
        self.pgrc_officer = User.objects.create_user('pgrc_off_sec', 'pgrco@example.com', 'Pass@123', role=User.Role.CASE_OFFICER, assigned_bureau=self.bureau_pgrc)

        # Institution
        self.inst = Institution.objects.create(
            aicte_permanent_id='1-SEC-999',
            name='National Security College of Engineering',
            region='NORTHERN',
            state='Delhi',
            district='New Delhi'
        )
        self.category = ComplaintCategory.objects.create(code='CAT_SEC', name='Regulatory Compliance')

        # Complaints
        self.complaint_rb = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-SEC01',
            institution=self.inst,
            title='RB Scrutiny Case',
            description='Detailed RB inspection finding.',
            category=self.category,
            currently_assigned_bureau=self.bureau_rb,
            currently_assigned_officer=self.rb_officer,
            created_by=self.rb_head
        )

        self.complaint_pgrc = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-SEC02',
            institution=self.inst,
            title='PGRC Grievance Case',
            description='Student fee grievance allegation.',
            category=self.category,
            currently_assigned_bureau=self.bureau_pgrc,
            currently_assigned_officer=self.pgrc_officer,
            created_by=self.pgrc_head
        )

        # Coordination Workspace between RB (Lead) and PGRC
        self.coordination = CoordinationService.initiate_coordination(
            title='Joint Review on Regulatory and Student Fee Allegations',
            coordinating_bureau=self.bureau_rb,
            participating_bureaus=[self.bureau_rb, self.bureau_pgrc],
            complaints=[self.complaint_rb, self.complaint_pgrc],
            created_by=self.rb_head,
            action_plan='Synchronized inspection on Friday.'
        )

    def test_sec01_unauthorized_coordination_detail_access_denied(self):
        """SEC01: Officers outside participating bureaus receive 403 Forbidden on coordination detail."""
        # ADV Bureau Head is not participating in this coordination
        self.client.force_login(self.adv_head)
        response = self.client.get(f'/coordination/{self.coordination.id}/')
        self.assertEqual(response.status_code, 403)

    def test_sec02_unauthorized_coordination_note_submission_denied(self):
        """SEC02: Non-participating officers cannot inject notes into shared coordination rooms."""
        self.client.force_login(self.adv_head)
        response = self.client.post(
            f'/coordination/{self.coordination.id}/notes/add/',
            {'note': 'Unauthorized note insertion'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CoordinationNote.objects.filter(note='Unauthorized note insertion').exists())

    def test_sec03_unrelated_bureau_head_cannot_change_coordination_status(self):
        """SEC03: Only Lead Bureau Head, Competent Authority, or Super Admin can modify coordination status."""
        # PGRC is participating member, but RB is the Lead Coordinating Bureau
        self.client.force_login(self.pgrc_head)
        response = self.client.post(
            f'/coordination/{self.coordination.id}/status-update/',
            {'status': 'RESOLVED', 'decision_summary': 'Unauthorized closure'}
        )
        self.assertEqual(response.status_code, 403)

        # RB Head (Lead) CAN update status
        self.client.force_login(self.rb_head)
        response_lead = self.client.post(
            f'/coordination/{self.coordination.id}/status-update/',
            {'status': 'IN_PROGRESS', 'decision_summary': 'Joint review active'}
        )
        self.assertEqual(response_lead.status_code, 302)
        self.coordination.refresh_from_db()
        self.assertEqual(self.coordination.coordination_status, 'IN_PROGRESS')

    def test_sec04_complaint_read_access_does_not_grant_upload_permission(self):
        """SEC04: Read-only access to a complaint does not authorize uploading documents."""
        # Regional officer has read access to complaints in their region, but NOT upload rights
        ro = User.objects.create_user('ro_sec', 'ro@example.com', 'Pass@123', role=User.Role.REGIONAL_OFFICER, authorized_region='NORTHERN')
        self.client.force_login(ro)

        pdf_content = b"%PDF-1.4 valid test pdf content"
        upload_file = SimpleUploadedFile("inspection.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            f'/complaints/{self.complaint_rb.id}/documents/upload/',
            {'file': upload_file, 'classification': 'INTERNAL_ONLY'}
        )
        self.assertEqual(response.status_code, 403)

    def test_sec05_document_classification_permissions_enforced(self):
        """SEC05: Classified CONFIDENTIAL documents are restricted from unauthorized officers."""
        pdf_content = b"%PDF-1.4 confidential scrutiny note"
        upload_file = SimpleUploadedFile("confidential_memo.pdf", pdf_content, content_type="application/pdf")
        doc = validate_and_save_document(
            complaint=self.complaint_rb,
            file_obj=upload_file,
            user=self.rb_officer,
            classification=ComplaintDocument.Classification.CONFIDENTIAL
        )

        # PGRC officer has no clearance for RB confidential document
        self.client.force_login(self.pgrc_officer)
        res = self.client.get(f'/complaints/{self.complaint_rb.id}/documents/{doc.id}/download/')
        self.assertEqual(res.status_code, 403)

        # Assigned RB officer has clearance
        self.client.force_login(self.rb_officer)
        res_ok = self.client.get(f'/complaints/{self.complaint_rb.id}/documents/{doc.id}/download/')
        self.assertEqual(res_ok.status_code, 200)

    def test_sec06_case_officer_cannot_view_unrelated_intelligence_candidates(self):
        """SEC06: Officers cannot view overlap candidates for bureaus they are not authorized in."""
        candidate = OverlapCandidate.objects.create(
            first_complaint=self.complaint_rb,
            second_complaint=self.complaint_pgrc,
            combined_score=0.75,
            review_status='PENDING'
        )

        # ADV Head has no involvement in RB or PGRC
        self.client.force_login(self.adv_head)
        res = self.client.get(f'/intelligence/candidate/{candidate.id}/')
        self.assertEqual(res.status_code, 403)

    def test_sec07_malicious_file_header_rejected(self):
        """SEC07: Files with fake extensions but invalid magic byte headers are rejected."""
        fake_pdf = SimpleUploadedFile("malicious.pdf", b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_and_save_document(
                complaint=self.complaint_rb,
                file_obj=fake_pdf,
                user=self.rb_officer
            )

    def test_sec08_production_settings_enforce_security_parameters(self):
        """SEC08: Production configuration fails startup if DJANGO_SECRET_KEY is missing or default."""
        old_val = os.environ.get('DJANGO_SECRET_KEY')
        try:
            os.environ['DJANGO_SECRET_KEY'] = 'augis-default-secret-key-aicte-2026'
            with self.assertRaises(ImproperlyConfigured):
                import importlib
                import config.settings.production
                importlib.reload(config.settings.production)
        finally:
            if old_val:
                os.environ['DJANGO_SECRET_KEY'] = old_val
            else:
                os.environ.pop('DJANGO_SECRET_KEY', None)
