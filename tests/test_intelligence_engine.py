from django.test import TestCase
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, CaseRelationship
from apps.intelligence.models import OverlapCandidate
from apps.intelligence.services import OverlapDetectionService

class IntelligenceEngineTests(TestCase):
    def setUp(self):
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.reviewer = User.objects.create_user(
            username='reviewer_head',
            email='reviewer@test.gov.in',
            password='TestPassword@123',
            role=User.Role.BUREAU_HEAD,
            assigned_bureau=self.bureau_rb,
            display_name='Reviewer Head'
        )

        self.institution = Institution.objects.create(
            aicte_permanent_id='1-AICTE-NLP-MATCH',
            name='National Institute of Engineering Research',
            institution_type='ENGINEERING',
            address='Knowledge Corridor',
            district='Bengaluru',
            state='Karnataka',
            region='SOUTH_WEST',
            pincode='560001'
        )

        self.cat_infra = ComplaintCategory.objects.create(
            code='INFRA_LAB',
            name='Laboratory Infrastructure Deficiencies',
            default_sla_days=30
        )

        self.cat_ragging = ComplaintCategory.objects.create(
            code='RAGGING',
            name='Ragging and Discipline',
            default_sla_days=7
        )

    def test_t11_two_active_cross_bureau_cases_trigger_detection(self):
        """T11: Two active cases from different Bureaus against same institution trigger detection."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-001',
            institution=self.institution,
            title='Inadequate Laboratory Equipment',
            description='Computer science and electronics laboratories lack mandated oscilloscope and workstation units.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.UNDER_PROCESS
        )

        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-002',
            institution=self.institution,
            title='Severe Deficiencies in Computing Lab Facilities',
            description='Students cannot conduct practical exams due to broken laboratory workstations and missing equipment.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc,
            current_status=Complaint.Status.PENDING
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        self.assertTrue(len(candidates) >= 1)
        cand = candidates[0]
        self.assertTrue(cand.is_cross_bureau)
        self.assertEqual(cand.first_complaint.institution, cand.second_complaint.institution)

    def test_t12_similar_issue_descriptions_generate_high_similarity_score(self):
        """T12: Similar issue descriptions generate an overlap candidate with semantic score."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-010',
            institution=self.institution,
            title='Unapproved B.Tech Artificial Intelligence Degree',
            description='The college is admitting students into unapproved AI program without AICTE approval.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )

        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-020',
            institution=self.institution,
            title='Unauthorized Artificial Intelligence Course Admissions',
            description='Institution running unapproved artificial intelligence branch with invalid degree promises.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        self.assertTrue(len(candidates) >= 1)
        self.assertTrue(candidates[0].combined_score >= 0.5)

    def test_t13_different_issues_against_same_institution_distinguished(self):
        """T13: Different issues against same institution are not classified as duplicate reports."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-030',
            institution=self.institution,
            title='Building Fire Safety Non-Compliance',
            description='Campus main building lacks fire exits and municipal fire clearance certificate.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )

        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-040',
            institution=self.institution,
            title='Hostel Ragging Complaint',
            description='First year student subjected to verbal harassment by senior hostel inmates in block B.',
            category=self.cat_ragging,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        cand = OverlapCandidate.objects.filter(
            first_complaint=c1, second_complaint=c2
        ).first()

        if cand:
            # Semantic text similarity between fire safety and hostel ragging is low
            self.assertTrue(cand.semantic_similarity < 0.45)

    def test_t14_reviewer_can_confirm_a_relationship(self):
        """T14: Reviewer can confirm a detected relationship, establishing CaseRelationship."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-050',
            institution=self.institution,
            title='Faculty salary delay',
            description='Faculty not paid salaries for 4 months.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )
        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-051',
            institution=self.institution,
            title='Faculty wage non-payment',
            description='Teachers unpaid for 4 months in violation of norms.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        cand = candidates[0]

        confirmed = OverlapDetectionService.confirm_overlap(
            cand.id, self.reviewer, 'Confirmed identical issue across bureaus.'
        )

        self.assertEqual(confirmed.review_status, OverlapCandidate.ReviewStatus.CONFIRMED)
        self.assertTrue(CaseRelationship.objects.filter(
            relationship_type=CaseRelationship.RelationType.CONFIRMED_RELATED
        ).exists())

    def test_t15_reviewer_can_reject_false_positive_suggestion(self):
        """T15: Reviewer can reject a false-positive suggestion with dismissal remarks."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-060',
            institution=self.institution,
            title='Hostel sanitation',
            description='Water filter broken in hostel.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )
        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-061',
            institution=self.institution,
            title='Campus Wi-Fi connectivity',
            description='Internet slow in library.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc
        )

        cand = OverlapCandidate.objects.create(
            first_complaint=c1,
            second_complaint=c2,
            institution_match_type=OverlapCandidate.MatchType.EXACT_PERMANENT_ID,
            combined_score=0.55
        )

        dismissed = OverlapDetectionService.dismiss_overlap(
            cand.id, self.reviewer, 'Unrelated facilities issues.'
        )
        self.assertEqual(dismissed.review_status, OverlapCandidate.ReviewStatus.DISMISSED)

    def test_t16_ai_model_failure_does_not_break_normal_complaint_registration(self):
        """T16: If NLP/transformers encounter an issue, complaint registration persists cleanly."""
        from unittest.mock import patch

        with patch('apps.intelligence.services.OverlapDetectionService.detect_overlaps_for_complaint') as mock_ai:
            mock_ai.side_effect = RuntimeError("Simulated transformer failure")
            from apps.complaints.services import create_complaint

            complaint = create_complaint(
                institution=self.institution,
                title='Resilience Test',
                description='Testing AI fallback resilience',
                category=self.cat_infra,
                bureau=self.bureau_rb,
                source_channel='PORTAL',
                created_by=self.reviewer
            )

            self.assertIsNotNone(complaint.id)
            self.assertEqual(complaint.current_status, Complaint.Status.PENDING)

    def test_t17_overlap_review_never_automatically_closes_complaints(self):
        """T17: Confirming or dismissing an overlap never modifies complaint status to DISPOSED."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-070',
            institution=self.institution,
            title='Case A under review',
            description='Description A',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.UNDER_PROCESS
        )
        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-071',
            institution=self.institution,
            title='Case B under review',
            description='Description B',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc,
            current_status=Complaint.Status.UNDER_PROCESS
        )

        cand = OverlapCandidate.objects.create(
            first_complaint=c1,
            second_complaint=c2,
            combined_score=0.85
        )

        OverlapDetectionService.confirm_overlap(cand.id, self.reviewer, 'Confirmed overlap')

        c1.refresh_from_db()
        c2.refresh_from_db()

        self.assertEqual(c1.current_status, Complaint.Status.UNDER_PROCESS)
        self.assertEqual(c2.current_status, Complaint.Status.UNDER_PROCESS)
