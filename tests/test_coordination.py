from django.test import TestCase
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory
from apps.coordination.services import CoordinationService
from apps.coordination.models import CoordinationRecord

class CoordinationWorkspaceTests(TestCase):
    def setUp(self):
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.head_rb = User.objects.create_user(
            username='head_rb',
            email='head_rb@test.gov.in',
            password='TestPassword@123',
            role=User.Role.BUREAU_HEAD,
            assigned_bureau=self.bureau_rb
        )

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-AICTE-COORD-TEST',
            name='Coordination Test Institute',
            institution_type='ENGINEERING',
            address='Industrial Estate',
            district='Hyderabad',
            state='Telangana',
            region='SOUTH_WEST',
            pincode='500001'
        )

        self.cat = ComplaintCategory.objects.create(code='CAT_COORD', name='Coordination Testing')

        self.c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-0099',
            institution=self.inst,
            title='RB Case on Affiliation',
            description='Affiliation norms dispute',
            category=self.cat,
            currently_assigned_bureau=self.bureau_rb
        )

        self.c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-0099',
            institution=self.inst,
            title='PGRC Case on Examination',
            description='Exam dispute',
            category=self.cat,
            currently_assigned_bureau=self.bureau_pgrc
        )

    def test_t18_coordination_records_preserve_original_case_identities(self):
        """T18: Joint coordination record links cases without modifying or merging their IDs."""
        original_c1_id = self.c1.id
        original_c1_no = self.c1.complaint_no
        original_c2_id = self.c2.id
        original_c2_no = self.c2.complaint_no

        coord = CoordinationService.initiate_coordination(
            title='Joint Scrutiny on Hyderabad Campus',
            coordinating_bureau=self.bureau_rb,
            participating_bureaus=[self.bureau_rb, self.bureau_pgrc],
            complaints=[self.c1, self.c2],
            created_by=self.head_rb,
            action_plan='Joint inspection of examination halls and student registries.'
        )

        self.assertIsNotNone(coord.id)
        self.assertTrue(coord.coordination_no.startswith('COORD-'))
        self.assertEqual(coord.related_complaints.count(), 2)

        # Confirm original complaint IDs are unchanged
        self.c1.refresh_from_db()
        self.c2.refresh_from_db()

        self.assertEqual(self.c1.id, original_c1_id)
        self.assertEqual(self.c1.complaint_no, original_c1_no)
        self.assertEqual(self.c2.id, original_c2_id)
        self.assertEqual(self.c2.complaint_no, original_c2_no)
        self.assertEqual(self.c1.currently_assigned_bureau, self.bureau_rb)
        self.assertEqual(self.c2.currently_assigned_bureau, self.bureau_pgrc)
