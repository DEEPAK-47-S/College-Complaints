import pytest
import datetime
import json
from django.utils import timezone
from django.urls import reverse
from django.test import Client
from apps.accounts.models import User, EmailOTP, PublicEmailOTP
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintAction

@pytest.mark.django_db
class TestBugBountyBoundaries:

    @pytest.fixture(autouse=True)
    def setup_base(self):
        self.client = Client()
        self.bureau, _ = Bureau.objects.get_or_create(
            code="PGRC",
            defaults={"name": "Public Grievance Redressal Cell"}
        )
        self.category, _ = ComplaintCategory.objects.get_or_create(
            name="Fee Extortion / Capitation Fee",
            defaults={"code": "FEE", "default_sla_days": 15}
        )
        self.institution, _ = Institution.objects.get_or_create(
            aicte_permanent_id="1-BB-TEST-01",
            defaults={
                "name": "Boundary Test Institute of Technology",
                "normalized_name": "boundary test institute of technology",
                "district": "Chennai",
                "state": "Tamil Nadu"
            }
        )
        self.officer, _ = User.objects.get_or_create(
            username="bb_officer",
            defaults={
                "email": "bb_officer@aicte-india.org",
                "display_name": "Boundary Officer",
                "role": User.Role.CASE_OFFICER,
                "is_active": True,
                "assigned_bureau": self.bureau
            }
        )
        self.officer.set_password("Augis@2026!Demo")
        self.officer.save()

    def test_open_redirect_boundary(self):
        """Validates that external open redirect attacks are strictly neutralized."""
        malicious_urls = [
            "https://evil-phishing-site.com",
            "http://attacker.org/steal-cookies",
            "//evil.com/redirect",
            "javascript:alert(1)"
        ]
        for bad_url in malicious_urls:
            resp = self.client.post(reverse('accounts:login') + f"?next={bad_url}", {
                'username': 'bb_officer',
                'password': 'Augis@2026!Demo'
            })
            # Should NOT redirect to the malicious site
            if resp.status_code == 302:
                redirect_target = resp.url
                assert "evil" not in redirect_target
                assert "attacker" not in redirect_target

    def test_citizen_pii_masked_in_public_timeline(self):
        """Ensures citizen emails or phone numbers are never leaked to public anonymous visitors."""
        complaint = Complaint.objects.create(
            complaint_no="AICTE-2026-PGRC-99001",
            institution=self.institution,
            title="Privacy Leak Check Complaint",
            description="Testing timeline privacy bounds",
            category=self.category,
            currently_assigned_bureau=self.bureau,
            complainant_name="Secret Citizen",
            complainant_email="secret_student_47@gmail.com",
            complainant_phone="9876543210"
        )
        # Create an action with citizen PII in remarks
        ComplaintAction.objects.create(
            complaint=complaint,
            action_type=ComplaintAction.ActionType.CREATED,
            remarks="Grievance registered by Secret Citizen (secret_student_47@gmail.com) from 9876543210"
        )

        resp = self.client.get(reverse('public:detail', kwargs={'complaint_no': complaint.complaint_no}))
        assert resp.status_code == 200
        content = resp.content.decode('utf-8')
        # Ensure email is masked in the rendered public response
        assert "secret_student_47@gmail.com" not in content
        assert "[CONFIDENTIAL-EMAIL]" in content

    def test_public_otp_flooding_rate_limit(self):
        """Ensures public OTP requests enforce a 60-second cooldown rate limit."""
        email = "citizen_rate_test@gmail.com"
        # First request -> 200 OK
        resp1 = self.client.post(reverse('public:send_otp'), {'email': email})
        assert resp1.status_code == 200
        data1 = json.loads(resp1.content.decode('utf-8'))
        assert data1['success'] is True

        # Immediate second request -> 429 Too Many Requests
        resp2 = self.client.post(reverse('public:send_otp'), {'email': email})
        assert resp2.status_code == 429
        data2 = json.loads(resp2.content.decode('utf-8'))
        assert data2['success'] is False
        assert "60 seconds" in data2['message']

    def test_email_format_validation_boundary(self):
        """Ensures invalid or malformed email inputs are safely rejected."""
        invalid_emails = [
            "not-an-email",
            "citizen@",
            "@domain.com",
            "<script>alert(1)</script>",
            "name@.com"
        ]
        for bad_email in invalid_emails:
            resp = self.client.post(reverse('public:send_otp'), {'email': bad_email})
            assert resp.status_code == 400
            data = json.loads(resp.content.decode('utf-8'))
            assert data['success'] is False

    def test_submission_field_length_boundaries(self):
        """Ensures fields exceeding database character caps are caught gracefully with validation errors."""
        session = self.client.session
        session['verified_public_email'] = "verified_student@gmail.com"
        session.save()

        # Title > 255 chars
        resp_long_title = self.client.post(reverse('public:submit'), {
            'email': 'verified_student@gmail.com',
            'full_name': 'Test Student',
            'mobile_number': '9876543210',
            'category': str(self.category.id),
            'institution': str(self.institution.id),
            'title': 'A' * 300,
            'description': 'Valid grievance description with sufficient characters.',
            'issue_location': 'Campus Block B',
            'area': 'South District'
        })
        assert resp_long_title.status_code == 200  # Rerenders form with error message
        content = resp_long_title.content.decode('utf-8')
        assert "Title is too long" in content

        # Non-numeric mobile number
        resp_bad_mobile = self.client.post(reverse('public:submit'), {
            'email': 'verified_student@gmail.com',
            'full_name': 'Test Student',
            'mobile_number': 'abcdefghijk',
            'category': str(self.category.id),
            'institution': str(self.institution.id),
            'title': 'Valid Title',
            'description': 'Valid grievance description with sufficient characters.',
            'issue_location': 'Campus Block B',
            'area': 'South District'
        })
        assert resp_bad_mobile.status_code == 200
        content_mobile = resp_bad_mobile.content.decode('utf-8')
        assert "Mobile Number is required" in content_mobile

    def test_tracking_id_sanitization_boundary(self):
        """Ensures special characters or XSS payloads in tracking URL are safely handled."""
        malicious_ids = [
            "AICTE-2026-INVALID-99999",
            "AICTE' OR '1'='1",
            "<script>alert(1)</script>"
        ]
        for bad_id in malicious_ids:
            resp = self.client.get(f"/complaint/{bad_id}/")
            # Should safely handle: redirect to track or return 404, never 500
            assert resp.status_code in [302, 404]

    def test_rbac_unauthenticated_boundaries(self):
        """Ensures all internal dashboard endpoints strictly require authenticated sessions."""
        protected_urls = [
            '/dashboard/',
            '/complaints/',
            '/institutions/',
            '/intelligence/',
            '/coordination/',
            '/notifications/',
            '/reports/',
            '/admin_panel/'
        ]
        for url in protected_urls:
            resp = self.client.get(url)
            assert resp.status_code in [302, 403, 404]
            if resp.status_code == 302:
                assert "/accounts/login/" in resp.url
