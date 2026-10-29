import threading
from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, CaseRelationship
from apps.complaints.services import generate_complaint_number
from apps.coordination.services import generate_coordination_number
from apps.intelligence.models import OverlapCandidate

class DatabaseV2TestCase(TransactionTestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')
        self.inst = Institution.objects.create(
            aicte_permanent_id='1-DB-001',
            name='DB Concurrency College',
            region='WESTERN',
            state='Maharashtra',
            district='Pune'
        )
        self.category = ComplaintCategory.objects.create(code='CAT_DB', name='Academic')

    def test_db01_concurrent_complaint_number_generation(self):
        """DB01: Multi-threaded concurrent calls generate unique, collision-free complaint IDs."""
        generated_numbers = []
        errors = []

        def worker():
            try:
                num = generate_complaint_number('PGRC', 2026)
                generated_numbers.append(num)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered thread errors: {errors}")
        self.assertEqual(len(generated_numbers), 10)
        self.assertEqual(len(set(generated_numbers)), 10, "Duplicate complaint numbers generated under concurrent threads!")

    def test_db02_concurrent_coordination_number_generation(self):
        """DB02: Multi-threaded concurrent calls generate unique coordination numbers."""
        generated_numbers = []
        errors = []

        def worker():
            try:
                num = generate_coordination_number()
                generated_numbers.append(num)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered thread errors: {errors}")
        self.assertEqual(len(generated_numbers), 10)
        self.assertEqual(len(set(generated_numbers)), 10, "Duplicate coordination numbers generated under concurrent threads!")

    def test_db03_prevent_self_referential_relationships(self):
        """DB03: Database CheckConstraint blocks linking a complaint to itself in CaseRelationship."""
        complaint = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-00999',
            institution=self.inst,
            title='Self-link test',
            description='Test self-linking',
            category=self.category,
            currently_assigned_bureau=self.bureau
        )

        with self.assertRaises(IntegrityError):
            CaseRelationship.objects.create(
                source_complaint=complaint,
                target_complaint=complaint,
                relationship_type=CaseRelationship.RelationType.CONFIRMED_RELATED
            )

    def test_db04_prevent_self_referential_overlaps(self):
        """DB04: Database CheckConstraint blocks overlap candidate with identical first and second complaints."""
        complaint = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-00998',
            institution=self.inst,
            title='Overlap self-link test',
            description='Test overlap self-linking',
            category=self.category,
            currently_assigned_bureau=self.bureau
        )

        with self.assertRaises(IntegrityError):
            OverlapCandidate.objects.create(
                first_complaint=complaint,
                second_complaint=complaint,
                combined_score=0.9
            )
