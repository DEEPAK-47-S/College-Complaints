from django.test import TestCase
from django.db import transaction
from django.db.utils import IntegrityError
from apps.institutions.models import Institution
from apps.institutions.forms import InstitutionForm

class InstitutionTests(TestCase):
    def setUp(self):
        self.inst = Institution.objects.create(
            aicte_permanent_id='1-AICTE-DUPLICATE',
            name='First Campus',
            institution_type='ENGINEERING',
            address='Address 1',
            district='Chennai',
            state='Tamil Nadu',
            region='SOUTHERN',
            pincode='600001'
        )

    def test_t04_duplicate_permanent_id_is_rejected_by_db(self):
        """T04 Part A: Duplicate institution AICTE Permanent ID is rejected by database constraint."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Institution.objects.create(
                    aicte_permanent_id='1-AICTE-DUPLICATE',
                    name='Second Campus',
                    institution_type='MANAGEMENT',
                    address='Address 2',
                    district='Chennai',
                    state='Tamil Nadu',
                    region='SOUTHERN',
                    pincode='600002'
                )

    def test_t04_duplicate_permanent_id_is_rejected_by_form(self):
        """T04 Part B: Duplicate institution AICTE Permanent ID is rejected by form validation."""
        form = InstitutionForm(data={
            'aicte_permanent_id': '1-AICTE-DUPLICATE',
            'name': 'Third Attempt',
            'institution_type': 'PHARMACY',
            'address': 'Address 3',
            'district': 'Chennai',
            'state': 'Tamil Nadu',
            'region': 'SOUTHERN',
            'pincode': '600003',
            'operational_status': 'ACTIVE'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('aicte_permanent_id', form.errors)
