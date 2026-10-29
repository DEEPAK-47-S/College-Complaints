import pytest
from django.urls import reverse
from apps.accounts.models import PublicEmailOTP, User
from apps.accounts.queryset_scoping import get_scoped_complaints
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintAction


@pytest.mark.django_db
class TestPublicPortal:
    def setup_method(self):
        self.bureau, _ = Bureau.objects.get_or_create(
            code='PGRC',
            defaults={'name': 'Public Grievance Redressal Cell'}
        )
        self.institution, _ = Institution.objects.get_or_create(
            aicte_permanent_id='TEST-INST-01',
            defaults={
                'name': 'Government College of Technology',
                'normalized_name': 'government college of technology',
                'district': 'Coimbatore',
                'state': 'Tamil Nadu',
                'region': 'SOUTHERN',
                'pincode': '641013'
            }
        )
        self.category, _ = ComplaintCategory.objects.get_or_create(
            code='INFRASTRUCTURE',
            defaults={'name': 'Infrastructure Deficiencies', 'default_sla_days': 30}
        )

    def test_public_homepage(self, client):
        response = client.get(reverse('public:index'))
        assert response.status_code == 200
        assert 'Centralized College & Student Grievance Redressal Portal'.encode('utf-8') in response.content

    def test_send_and_verify_otp(self, client):
        email = 'student@example.com'
        # Send OTP
        response = client.post(reverse('public:send_otp'), {'email': email})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify active OTP record was generated in DB
        otp_record = PublicEmailOTP.objects.filter(email=email, is_used=False).first()
        assert otp_record is not None
        assert len(otp_record.otp_code) == 6

        # Verify OTP
        verify_resp = client.post(reverse('public:verify_otp'), {
            'email': email,
            'otp': otp_record.otp_code
        })
        assert verify_resp.status_code == 200
        assert verify_resp.json()['success'] is True

        # Check session
        assert client.session.get('verified_public_email') == email

    def test_submit_complaint_and_all_officers_visibility(self, client):
        email = 'applicant@example.com'
        # Authenticate session with verified email
        session = client.session
        session['verified_public_email'] = email
        session.save()

        form_data = {
            'email': email,
            'full_name': 'Kavitha R',
            'mobile_number': '9842109876',
            'complainant_type': 'STUDENT',
            'institution': str(self.institution.id),
            'category': str(self.category.id),
            'title': 'Library AC and Internet Failure',
            'description': 'The campus central library internet connections have been broken for two weeks.',
            'issue_location': 'Central Library, 1st Floor Digital Reading Room',
            'area': 'Coimbatore',
            'priority': 'MEDIUM'
        }

        response = client.post(reverse('public:submit'), form_data)
        assert response.status_code == 302
        assert '/complaint/success/' in response.url

        # Check DB
        complaint = Complaint.objects.filter(complainant_email=email).first()
        assert complaint is not None
        assert complaint.complainant_name == 'Kavitha R'
        assert complaint.currently_assigned_bureau == self.bureau
        assert complaint.source_channel == Complaint.SourceChannel.PORTAL

        # Verify all officers across different bureaus can view public complaints in their scoped list
        other_bureau, _ = Bureau.objects.get_or_create(code='AB', defaults={'name': 'Approval Bureau'})
        case_officer = User.objects.create(
            username='case_officer_test',
            email='co@aicte.test',
            role=User.Role.CASE_OFFICER,
            assigned_bureau=other_bureau
        )
        bureau_head = User.objects.create(
            username='bureau_head_test',
            email='bh@aicte.test',
            role=User.Role.BUREAU_HEAD,
            assigned_bureau=other_bureau
        )
        regional_officer = User.objects.create(
            username='reg_officer_test',
            email='ro@aicte.test',
            role=User.Role.REGIONAL_OFFICER,
            authorized_region='NORTHERN'
        )

        assert get_scoped_complaints(case_officer).filter(id=complaint.id).exists()
        assert get_scoped_complaints(bureau_head).filter(id=complaint.id).exists()
        assert get_scoped_complaints(regional_officer).filter(id=complaint.id).exists()

        # Test success page
        success_resp = client.get(reverse('public:success', kwargs={'complaint_no': complaint.complaint_no}))
        assert success_resp.status_code == 200
        assert complaint.complaint_no.encode() in success_resp.content

        # Test track status
        track_resp = client.post(reverse('public:track'), {'complaint_id': complaint.complaint_no})
        assert track_resp.status_code == 302
        assert complaint.complaint_no in track_resp.url

        # Test detail page
        detail_resp = client.get(reverse('public:detail', kwargs={'complaint_no': complaint.complaint_no}))
        assert detail_resp.status_code == 200
        assert complaint.complaint_no.encode() in detail_resp.content
        assert 'Library AC and Internet Failure'.encode() in detail_resp.content
