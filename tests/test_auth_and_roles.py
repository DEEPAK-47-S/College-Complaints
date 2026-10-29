from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory

class AuthenticationAndRoleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.superadmin = User.objects.create_user(
            username='admin_test',
            email='admin@test.gov.in',
            password='TestPassword@123',
            role=User.Role.SUPER_ADMIN,
            display_name='Admin Test'
        )

        self.rb_officer = User.objects.create_user(
            username='rb_officer_test',
            email='rb@test.gov.in',
            password='TestPassword@123',
            role=User.Role.CASE_OFFICER,
            assigned_bureau=self.bureau_rb,
            display_name='RB Officer'
        )

        self.pgrc_officer = User.objects.create_user(
            username='pgrc_officer_test',
            email='pgrc@test.gov.in',
            password='TestPassword@123',
            role=User.Role.CASE_OFFICER,
            assigned_bureau=self.bureau_pgrc,
            display_name='PGRC Officer'
        )

        self.institution = Institution.objects.create(
            aicte_permanent_id='1-TEST-9999',
            name='Test Institute of Technology',
            institution_type='ENGINEERING',
            address='Test Campus',
            district='New Delhi',
            state='Delhi',
            region='NORTHERN',
            pincode='110001'
        )

        self.category = ComplaintCategory.objects.create(
            code='TEST_CAT',
            name='Test Category',
            default_sla_days=30
        )

        # Complaint strictly assigned to RB
        self.rb_complaint = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-99001',
            institution=self.institution,
            title='Test RB Case',
            description='Test grievance description for RB',
            category=self.category,
            currently_assigned_bureau=self.bureau_rb,
            currently_assigned_officer=self.rb_officer
        )

    def test_t01_authorized_login_succeeds(self):
        """T01: Authorized login succeeds with valid credentials and completes 2FA OTP verification."""
        from apps.accounts.models import EmailOTP
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'TestPassword@123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:verify_otp'))
        
        # Verify 2FA OTP step
        active_otp = EmailOTP.objects.filter(user=self.superadmin, is_used=False).latest('created_at')
        otp_response = self.client.post(reverse('accounts:verify_otp'), {
            'otp_code': active_otp.otp_code
        })
        self.assertEqual(otp_response.status_code, 302)
        self.assertEqual(otp_response.url, reverse('dashboard:index'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_t02_invalid_login_fails_safely(self):
        """T02: Invalid credentials fail safely without data leakage."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'WrongPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)
        self.assertContains(response, 'Invalid username or password')

    def test_t03_unauthorized_user_cannot_access_restricted_complaints(self):
        """T03: Officer from PGRC cannot view or modify RB's restricted complaint."""
        self.client.login(username='pgrc_officer_test', password='TestPassword@123')
        
        # Access RB complaint detail
        response = self.client.get(reverse('complaints:detail', args=[self.rb_complaint.id]))
        self.assertEqual(response.status_code, 403)
