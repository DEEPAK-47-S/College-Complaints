import uuid
from django.db import models
from django.conf import settings
from django.db.models import F, Q
from apps.complaints.models import Complaint

class OverlapCandidate(models.Model):
    class MatchType(models.TextChoices):
        EXACT_PERMANENT_ID = 'EXACT_PERMANENT_ID', 'Exact AICTE Permanent ID Match'
        NORMALIZED_NAME = 'NORMALIZED_NAME', 'Normalized Institution Name Match'
        REGIONAL_PROXIMITY = 'REGIONAL_PROXIMITY', 'Regional & Location Match'

    class DetectionCategory(models.TextChoices):
        INSTITUTION_CROSS_BUREAU = 'INSTITUTION_CROSS_BUREAU', 'Institution-Level Cross-Bureau Alert'
        POTENTIALLY_RELATED_ISSUE = 'POTENTIALLY_RELATED_ISSUE', 'Potentially Related Issue'
        DUAL_OVERLAP = 'DUAL_OVERLAP', 'Dual Overlap (Same Institution & Related Issue)'

    class ReviewStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Human Scrutiny'
        CONFIRMED = 'CONFIRMED', 'Confirmed Related Grievance'
        DISMISSED = 'DISMISSED', 'Dismissed as False Positive'
        SEPARATE_ISSUES = 'SEPARATE_ISSUES', 'Confirmed Distinct Separate Issues'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='overlaps_as_first'
    )
    second_complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='overlaps_as_second'
    )
    institution_match_type = models.CharField(
        max_length=50,
        choices=MatchType.choices,
        default=MatchType.EXACT_PERMANENT_ID
    )

    # Independent Detection Categories
    detection_category = models.CharField(
        max_length=50,
        choices=DetectionCategory.choices,
        default=DetectionCategory.POTENTIALLY_RELATED_ISSUE,
        db_index=True
    )
    is_institution_level_alert = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Multiple bureaus active on the same institution"
    )
    is_issue_level_overlap = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Substantive semantic or factual overlap in allegations"
    )

    category_similarity = models.FloatField(default=0.0)
    semantic_similarity = models.FloatField(default=0.0)
    combined_score = models.FloatField(default=0.0, db_index=True)
    matching_reasons = models.JSONField(default=list)
    gemini_analysis = models.JSONField(default=dict, blank=True)
    model_version = models.CharField(max_length=100, default='local-tfidf-minilm-hybrid')
    detection_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Human Review Audit Fields
    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_overlaps'
    )
    review_remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-combined_score', '-detection_timestamp']
        verbose_name = 'Overlap Candidate'
        verbose_name_plural = 'Overlap Candidates'
        constraints = [
            models.UniqueConstraint(
                fields=['first_complaint', 'second_complaint'],
                name='unique_canonical_overlap_pair'
            ),
            models.CheckConstraint(
                **({
                    'condition': ~models.Q(first_complaint=models.F('second_complaint'))
                } if 'condition' in getattr(models.CheckConstraint.__init__, '__code__', {}).co_varnames else {
                    'check': ~models.Q(first_complaint=models.F('second_complaint'))
                }),
                name='overlap_candidate_no_self_link'
            )
        ]

    def __str__(self):
        return f"Overlap: {self.first_complaint.complaint_no} & {self.second_complaint.complaint_no} ({self.combined_score:.2f})"

    @property
    def is_cross_bureau(self):
        return self.first_complaint.currently_assigned_bureau_id != self.second_complaint.currently_assigned_bureau_id

    @property
    def percentage_score(self):
        return int(round(self.combined_score * 100))

class IntelligenceJob(models.Model):
    """
    Durable asynchronous processing queue for NLP overlap detection.
    Allows complaint intake to commit immediately, moving heavy similarity
    computation to an on-commit hook or background management worker.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Processing'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed (Retry Available)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='intelligence_jobs'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Intelligence Background Job'
        verbose_name_plural = 'Intelligence Background Jobs'

    def __str__(self):
        return f"Job {self.id} for {self.complaint.complaint_no} [{self.status}]"
