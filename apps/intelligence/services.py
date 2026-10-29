import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from .models import OverlapCandidate, IntelligenceJob
from .vectorizer import compute_similarity, extract_shared_keywords
from apps.complaints.models import Complaint, CaseRelationship
from apps.audit.services import log_audit_event

logger = logging.getLogger('augis.intelligence')

class OverlapDetectionService:
    @staticmethod
    def detect_overlaps_for_complaint(target_complaint):
        """
        Executes the decoupled two-category matching pipeline for a complaint:
        - Category A: Institution-Level Cross-Bureau Alert (multiple bureaus investigating same institution)
        - Category B: Potentially Related Issue (substantive semantic similarity in grievances)
        Does NOT inflate semantic similarity scores with fixed institution weights.
        """
        institution = target_complaint.institution
        if not institution:
            return []

        # Stage 1: Candidate retrieval filtered by institution
        candidates_qs = Complaint.objects.filter(
            institution=institution
        ).exclude(
            id=target_complaint.id
        ).select_related(
            'institution', 'category', 'currently_assigned_bureau'
        )

        detected_candidates = []
        similarity_threshold = getattr(settings, 'SIMILARITY_THRESHOLD', 0.60)

        for candidate in candidates_qs:
            # Canonical pair ordering (lexicographical UUID comparison) to guarantee canonical unique pairs
            first_c, second_c = (
                (target_complaint, candidate)
                if str(target_complaint.id) < str(candidate.id)
                else (candidate, target_complaint)
            )

            # Check if candidate record already exists
            existing = OverlapCandidate.objects.filter(
                first_complaint=first_c,
                second_complaint=second_c
            ).first()

            if existing and existing.review_status in [
                OverlapCandidate.ReviewStatus.CONFIRMED,
                OverlapCandidate.ReviewStatus.DISMISSED,
                OverlapCandidate.ReviewStatus.SEPARATE_ISSUES
            ]:
                # Human review persistence: Never overwrite completed official review
                continue

            # Stage 2: Category A Evaluation - Institution-Level Cross-Bureau Alert
            is_cross_bureau = (target_complaint.currently_assigned_bureau_id != candidate.currently_assigned_bureau_id)
            is_target_active = target_complaint.current_status in ['PENDING', 'UNDER_PROCESS', 'ESCALATED']
            is_candidate_active = candidate.current_status in ['PENDING', 'UNDER_PROCESS', 'ESCALATED']
            is_institution_level_alert = is_cross_bureau and is_target_active and is_candidate_active

            # Stage 3: Category B Evaluation - Substantive Issue Similarity
            text1 = f"{target_complaint.title} {target_complaint.description}"
            text2 = f"{candidate.title} {candidate.description}"
            sem_sim, model_version = compute_similarity(text1, text2)
            is_same_category = (target_complaint.category_id == candidate.category_id)
            cat_score = 1.0 if is_same_category else 0.0

            # Substantive Issue Similarity: 65% semantic text similarity + 35% category correlation
            # NOTE: Institution match is NOT added as a score weight, preventing false duplicates
            combined_score = round(0.65 * sem_sim + 0.35 * cat_score, 4)

            # Issue-level overlap requires substantive semantic similarity
            shared_kw = extract_shared_keywords(text1, text2)
            is_issue_level_overlap = (
                sem_sim >= similarity_threshold or
                (combined_score >= 0.45 and (sem_sim >= 0.15 or len(shared_kw) > 0))
            )

            # Should an alert be generated?
            # Generate if:
            # 1. Multiple bureaus are actively investigating the same institution (Category A)
            # OR 2. Grievances share substantive factual/semantic overlap (Category B)
            if not (is_institution_level_alert or is_issue_level_overlap):
                continue

            # Determine explicit detection category
            if is_institution_level_alert and is_issue_level_overlap:
                detection_cat = OverlapCandidate.DetectionCategory.POTENTIALLY_RELATED_ISSUE
            elif is_institution_level_alert:
                detection_cat = OverlapCandidate.DetectionCategory.INSTITUTION_CROSS_BUREAU
            else:
                detection_cat = OverlapCandidate.DetectionCategory.POTENTIALLY_RELATED_ISSUE

            # Construct transparent, explainable reasons
            reasons = [
                f"Institution Match: {institution.name} (AICTE ID: {institution.aicte_permanent_id})"
            ]
            if is_cross_bureau:
                reasons.append(
                    f"Cross-Bureau: {first_c.currently_assigned_bureau.code} & {second_c.currently_assigned_bureau.code} active"
                )
            if is_same_category:
                reasons.append(f"Matching Category: {target_complaint.category.name}")
            else:
                reasons.append(f"Distinct Categories: {first_c.category.name} vs {second_c.category.name}")

            reasons.append(f"Semantic Text Similarity: {sem_sim * 100:.1f}%")
            if shared_kw:
                reasons.append(f"Shared Key Terms: {', '.join(shared_kw)}")

            # Create or update candidate record
            if existing:
                existing.detection_category = detection_cat
                existing.is_institution_level_alert = is_institution_level_alert
                existing.is_issue_level_overlap = is_issue_level_overlap
                existing.category_similarity = cat_score
                existing.semantic_similarity = sem_sim
                existing.combined_score = combined_score
                existing.matching_reasons = reasons
                existing.model_version = model_version
                existing.save()
                overlap_cand = existing
            else:
                overlap_cand = OverlapCandidate.objects.create(
                    first_complaint=first_c,
                    second_complaint=second_c,
                    institution_match_type=OverlapCandidate.MatchType.EXACT_PERMANENT_ID,
                    detection_category=detection_cat,
                    is_institution_level_alert=is_institution_level_alert,
                    is_issue_level_overlap=is_issue_level_overlap,
                    category_similarity=cat_score,
                    semantic_similarity=sem_sim,
                    combined_score=combined_score,
                    matching_reasons=reasons,
                    model_version=model_version,
                    review_status=OverlapCandidate.ReviewStatus.PENDING
                )

            detected_candidates.append(overlap_cand)

            # Auto-alert notifications if cross-bureau
            if is_cross_bureau:
                try:
                    from apps.notifications.services import NotificationService
                    NotificationService.send_cross_bureau_overlap_alert(overlap_cand)
                except Exception as notif_err:
                    logger.debug(f"Notification alert deferred: {notif_err}")

        return detected_candidates

    @classmethod
    def queue_intelligence_job(cls, complaint):
        """Creates a pending background intelligence job."""
        return IntelligenceJob.objects.create(
            complaint=complaint,
            status=IntelligenceJob.Status.PENDING
        )

    @classmethod
    def process_pending_jobs(cls, limit=50):
        """Processes pending background intelligence jobs."""
        pending_jobs = IntelligenceJob.objects.filter(
            status=IntelligenceJob.Status.PENDING
        ).select_related('complaint__institution')[:limit]

        processed_count = 0
        for job in pending_jobs:
            job.status = IntelligenceJob.Status.PROCESSING
            job.save(update_fields=['status'])
            try:
                cls.detect_overlaps_for_complaint(job.complaint)
                job.status = IntelligenceJob.Status.COMPLETED
                job.processed_at = timezone.now()
                job.save(update_fields=['status', 'processed_at'])
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed processing intelligence job {job.id}: {e}")
                job.status = IntelligenceJob.Status.FAILED
                job.error_message = str(e)
                job.retry_count += 1
                job.save(update_fields=['status', 'error_message', 'retry_count'])

        return processed_count

    @staticmethod
    def confirm_overlap(candidate_id, reviewer, remarks=''):
        """
        Authorized official confirms that the two complaints are related.
        Creates a confirmed CaseRelationship and updates audit logs.
        Never automatically disposes or alters original complaints!
        """
        with transaction.atomic():
            candidate = OverlapCandidate.objects.select_for_update().get(id=candidate_id)
            candidate.review_status = OverlapCandidate.ReviewStatus.CONFIRMED
            candidate.reviewed_by = reviewer
            candidate.review_remarks = remarks
            candidate.reviewed_at = timezone.now()
            candidate.save()

            # Record CaseRelationship (bidirectional so either side can query related complaints)
            CaseRelationship.objects.update_or_create(
                source_complaint=candidate.first_complaint,
                target_complaint=candidate.second_complaint,
                relationship_type=CaseRelationship.RelationType.CONFIRMED_RELATED,
                defaults={'remarks': remarks, 'created_by': reviewer}
            )
            CaseRelationship.objects.update_or_create(
                source_complaint=candidate.second_complaint,
                target_complaint=candidate.first_complaint,
                relationship_type=CaseRelationship.RelationType.CONFIRMED_RELATED,
                defaults={'remarks': remarks, 'created_by': reviewer}
            )

            log_audit_event(
                actor=reviewer,
                event_type="OVERLAP_CONFIRMED",
                entity_name="OverlapCandidate",
                entity_id=str(candidate.id),
                change_summary={
                    "first_case": candidate.first_complaint.complaint_no,
                    "second_case": candidate.second_complaint.complaint_no,
                    "remarks": remarks
                }
            )
        return candidate

    @staticmethod
    def dismiss_overlap(candidate_id, reviewer, remarks=''):
        """
        Dismisses a suggested candidate as a false-positive.
        """
        with transaction.atomic():
            candidate = OverlapCandidate.objects.select_for_update().get(id=candidate_id)
            candidate.review_status = OverlapCandidate.ReviewStatus.DISMISSED
            candidate.reviewed_by = reviewer
            candidate.review_remarks = remarks
            candidate.reviewed_at = timezone.now()
            candidate.save()

            log_audit_event(
                actor=reviewer,
                event_type="OVERLAP_DISMISSED",
                entity_name="OverlapCandidate",
                entity_id=str(candidate.id),
                change_summary={
                    "first_case": candidate.first_complaint.complaint_no,
                    "second_case": candidate.second_complaint.complaint_no,
                    "remarks": remarks
                }
            )
        return candidate

    @staticmethod
    def mark_as_separate_issues(candidate_id, reviewer, remarks=''):
        """
        Confirms complaints are against the same institution but represent completely separate issues.
        """
        with transaction.atomic():
            candidate = OverlapCandidate.objects.select_for_update().get(id=candidate_id)
            candidate.review_status = OverlapCandidate.ReviewStatus.SEPARATE_ISSUES
            candidate.reviewed_by = reviewer
            candidate.review_remarks = remarks
            candidate.reviewed_at = timezone.now()
            candidate.save()

            CaseRelationship.objects.update_or_create(
                source_complaint=candidate.first_complaint,
                target_complaint=candidate.second_complaint,
                relationship_type=CaseRelationship.RelationType.SEPARATE_ISSUES,
                defaults={'remarks': remarks, 'created_by': reviewer}
            )

            log_audit_event(
                actor=reviewer,
                event_type="OVERLAP_MARKED_SEPARATE",
                entity_name="OverlapCandidate",
                entity_id=str(candidate.id),
                change_summary={
                    "first_case": candidate.first_complaint.complaint_no,
                    "second_case": candidate.second_complaint.complaint_no,
                    "remarks": remarks
                }
            )
        return candidate
