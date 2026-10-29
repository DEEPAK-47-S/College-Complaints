from django.test import TestCase
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory, CaseRelationship
from apps.intelligence.models import OverlapCandidate, IntelligenceJob
from apps.intelligence.services import OverlapDetectionService
from apps.intelligence.vectorizer import normalize_text, compute_similarity

class IntelligenceV2TestCase(TestCase):
    def setUp(self):
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-AI-101',
            name='Bharath Institute of Technology',
            region='SOUTHERN',
            state='Tamil Nadu',
            district='Chennai'
        )

        self.cat_infra = ComplaintCategory.objects.create(code='INFRA', name='Physical Infrastructure Deficiency')
        self.cat_exam = ComplaintCategory.objects.create(code='EXAM', name='Examination Malpractice')

    def test_ai01_same_institution_unrelated_issue_distinct(self):
        """AI01: Two completely unrelated complaints on the same institution are flagged as Institution Alert (Cat A) but NOT related issue (Cat B)."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-AI01',
            institution=self.inst,
            title='Inadequate Fire Extinguishers and Emergency Exit Blocks',
            description='Severe fire safety violations with blocked emergency exits and expired fire extinguishers in block B.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )

        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-AI01',
            institution=self.inst,
            title='Faculty Leaking Semester Exam Question Papers',
            description='Students caught copying using leaked question papers allegedly distributed by chemistry faculty before exam.',
            category=self.cat_exam,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]

        # Verify Category A is True, but Category B (substantive issue overlap) is False
        self.assertTrue(candidate.is_institution_level_alert, "Should be flagged as institution-level cross-bureau alert")
        self.assertFalse(candidate.is_issue_level_overlap, "Unrelated fire safety and exam leak issues must NOT be marked as related issue!")
        self.assertEqual(candidate.detection_category, OverlapCandidate.DetectionCategory.INSTITUTION_CROSS_BUREAU)

    def test_ai02_same_institution_related_issue_detected(self):
        """AI02: Grievances alleging related laboratory deficiencies against same college are detected with substantive overlap."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-AI02',
            institution=self.inst,
            title='Computer Science Laboratory Deficiencies',
            description='The computer science laboratories lack licensed operating systems, functional machines, and internet connectivity.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )

        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-AI02',
            institution=self.inst,
            title='Broken Hardware in CS Laboratories',
            description='Computer science laboratory has broken computers and non-functioning hardware preventing practical programming classes.',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]

        self.assertTrue(candidate.is_issue_level_overlap, "Related laboratory issues must be detected as issue-level overlap")
        self.assertGreater(candidate.combined_score, 0.45)

    def test_ai04_tamil_unicode_preservation(self):
        """AI04: Tamil Unicode characters are preserved during normalization and text matching."""
        tamil_text = "கல்லூரி கட்டண உயர்வு மற்றும் ஆய்வக குறைபாடுகள்"
        normalized = normalize_text(tamil_text)
        self.assertIn("கல்லூரி", normalized, "Tamil characters must not be wiped out by regex normalization!")

        # Similar Tamil texts
        t1 = "கல்லூரி ஆய்வக குறைபாடுகள் மற்றும் கணினி பழுது"
        t2 = "கல்லூரி ஆய்வக குறைபாடுகள் மற்றும் உபகரணங்கள் பழுது"
        sim, _ = compute_similarity(t1, t2)
        self.assertGreater(sim, 0.4, f"Tamil similarity should be recognized (got {sim})")

    def test_ai05_hindi_unicode_preservation(self):
        """AI05: Hindi Devanagari characters are preserved and correctly compared."""
        h1 = "संस्थान में प्रयोगशाला उपकरणों की भारी कमी है"
        h2 = "संस्थान में प्रयोगशाला और कंप्यूटर की भारी कमी"
        sim, _ = compute_similarity(h1, h2)
        self.assertGreater(sim, 0.4, f"Hindi similarity should be recognized (got {sim})")

    def test_ai08_human_review_persistence(self):
        """AI08: A candidate dismissed or confirmed by a human reviewer is never overwritten by subsequent engine executions."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-AI08',
            institution=self.inst,
            title='Issue A',
            description='Faculty salary issue',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )
        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-AI08',
            institution=self.inst,
            title='Issue B',
            description='Faculty salary delay',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]

        # Dismiss candidate
        from apps.accounts.models import User
        reviewer = User.objects.create_user('reviewer_ai', 'rev@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_rb)
        OverlapDetectionService.dismiss_overlap(candidate.id, reviewer, "False positive - distinct batches")

        candidate.refresh_from_db()
        self.assertEqual(candidate.review_status, OverlapCandidate.ReviewStatus.DISMISSED)

        # Run engine again
        OverlapDetectionService.detect_overlaps_for_complaint(c2)
        candidate.refresh_from_db()
        self.assertEqual(candidate.review_status, OverlapCandidate.ReviewStatus.DISMISSED, "Reviewer decision must persist!")

    def test_ai09_original_complaints_unaffected_by_overlap_decisions(self):
        """AI09: Confirming an overlap creates CaseRelationship but never closes or alters original complaint status."""
        c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-AI09',
            institution=self.inst,
            title='Hostel Issue A',
            description='Hostel cleanliness issue',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_rb
        )
        c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-AI09',
            institution=self.inst,
            title='Hostel Issue B',
            description='Hostel water supply issue',
            category=self.cat_infra,
            currently_assigned_bureau=self.bureau_pgrc
        )

        candidates = OverlapDetectionService.detect_overlaps_for_complaint(c2)
        candidate = candidates[0]

        from apps.accounts.models import User
        reviewer = User.objects.create_user('rev2_ai', 'rev2@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_rb)
        OverlapDetectionService.confirm_overlap(candidate.id, reviewer, "Both relate to student residential welfare.")

        c1.refresh_from_db()
        c2.refresh_from_db()
        self.assertEqual(c1.current_status, Complaint.Status.PENDING)
        self.assertEqual(c2.current_status, Complaint.Status.PENDING)
        self.assertTrue(CaseRelationship.objects.filter(source_complaint=c1, target_complaint=c2).exists())
