import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.institutions.models import Institution
from apps.bureaus.models import Bureau

class ComplaintCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text="e.g. CAPITATION_FEE, FACULTY_DEFICIENCY")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    default_sla_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Complaint Category'
        verbose_name_plural = 'Complaint Categories'

    def __str__(self):
        return self.name

class Complaint(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        UNDER_PROCESS = 'UNDER_PROCESS', 'Under Process'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'
        ESCALATED = 'ESCALATED', 'Escalated'
        DISPOSED = 'DISPOSED', 'Disposed'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class SourceChannel(models.TextChoices):
        PORTAL = 'PORTAL', 'Online Web Portal'
        CPGRAMS_FORWARD = 'CPGRAMS_FORWARD', 'CPGRAMS Forward'
        EMAIL = 'EMAIL', 'Official Email'
        PHYSICAL_LETTER = 'PHYSICAL_LETTER', 'Physical Letter / Petition'
        REGULATORY_INSPECTION = 'REGULATORY_INSPECTION', 'Regulatory Inspection Finding'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint_no = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique Human-Readable ID, e.g. AICTE-2026-PGRC-00104"
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name='complaints',
        help_text="Target Educational Institution"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Original grievance / complaint description")
    category = models.ForeignKey(
        ComplaintCategory,
        on_delete=models.PROTECT,
        related_name='complaints'
    )
    source_channel = models.CharField(
        max_length=50,
        choices=SourceChannel.choices,
        default=SourceChannel.PORTAL
    )
    external_reference_no = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional external ID (CPGRAMS ref, diary no, court case no)"
    )
    date_received = models.DateField(default=timezone.now, db_index=True)
    current_status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )
    currently_assigned_bureau = models.ForeignKey(
        Bureau,
        on_delete=models.PROTECT,
        related_name='assigned_complaints'
    )
    currently_assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_complaints'
    )
    last_action_date = models.DateTimeField(auto_now=True)
    next_action_required = models.CharField(max_length=255, blank=True)
    expected_disposal_date = models.DateField(null=True, blank=True, db_index=True)
    applicable_sla_policy = models.ForeignKey(
        'notifications.SLAPolicy',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='governed_complaints'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='registered_complaints'
    )
    disposed_at = models.DateTimeField(null=True, blank=True)
    closure_remarks = models.TextField(blank=True)
    
    # Public Complainant Details (Bilingual Grievance Portal)
    complainant_name = models.CharField(max_length=150, blank=True, default='')
    complainant_email = models.EmailField(blank=True, default='')
    complainant_phone = models.CharField(max_length=20, blank=True, default='')
    complainant_type = models.CharField(
        max_length=50,
        blank=True,
        default='STUDENT',
        help_text="Student, Faculty, Parent, or Public Complainant"
    )
    issue_location = models.CharField(max_length=255, blank=True, default='', help_text="Campus Block, Department, Lab, Hostel or Street Location")
    area = models.CharField(max_length=150, blank=True, default='', help_text="Area / District / Ward")
    is_email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'
        indexes = [
            models.Index(fields=['currently_assigned_bureau', 'current_status']),
            models.Index(fields=['institution', 'current_status']),
            models.Index(fields=['current_status', 'expected_disposal_date']),
        ]

    def __str__(self):
        return f"{self.complaint_no} - {self.title[:40]}"

    @property
    def is_overdue(self):
        if self.current_status == self.Status.DISPOSED:
            return False
        if not self.expected_disposal_date:
            return False
        return timezone.now().date() > self.expected_disposal_date

    @property
    def days_open(self):
        end = self.disposed_at.date() if (self.disposed_at and self.current_status == self.Status.DISPOSED) else timezone.now().date()
        return (end - self.date_received).days

class ComplaintDocument(models.Model):
    class Classification(models.TextChoices):
        INTERNAL_ONLY = 'INTERNAL_ONLY', 'Internal AICTE Only'
        CONFIDENTIAL = 'CONFIDENTIAL', 'Confidential Scrutiny Evidence'
        PUBLIC_SUMMARY = 'PUBLIC_SUMMARY', 'Disclosable Summary'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file = models.FileField(upload_to='complaints_private/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    stored_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField(help_text="Size in bytes")
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_documents'
    )
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    visibility_classification = models.CharField(
        max_length=30,
        choices=Classification.choices,
        default=Classification.INTERNAL_ONLY
    )
    checksum = models.CharField(max_length=64, help_text="SHA-256 Checksum")

    class Meta:
        ordering = ['-upload_timestamp']
        verbose_name = 'Complaint Document'
        verbose_name_plural = 'Complaint Documents'

    def __str__(self):
        return f"{self.original_filename} ({self.complaint.complaint_no})"

    @property
    def file_extension(self):
        import os
        return os.path.splitext(self.original_filename)[1].lower().lstrip('.')

    @property
    def icon_class(self):
        ext = self.file_extension
        if ext in ['pdf']:
            return 'bi-file-earmark-pdf text-danger'
        elif ext in ['doc', 'docx']:
            return 'bi-file-earmark-word text-primary'
        elif ext in ['xls', 'xlsx', 'csv']:
            return 'bi-file-earmark-excel text-success'
        elif ext in ['png', 'jpg', 'jpeg', 'gif']:
            return 'bi-file-earmark-image text-info'
        elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
            return 'bi-file-earmark-zip text-warning'
        return 'bi-file-earmark-text text-secondary'

class ComplaintAction(models.Model):
    class ActionType(models.TextChoices):
        CREATED = 'CREATED', 'Complaint Registered'
        ASSIGNED = 'ASSIGNED', 'Case Officer Assigned'
        REASSIGNED = 'REASSIGNED', 'Reassigned to Different Officer'
        STATUS_CHANGE = 'STATUS_CHANGE', 'Status Changed'
        TRANSFER_REQUEST = 'TRANSFER_REQUEST', 'Inter-Bureau Transfer Requested'
        TRANSFER_APPROVED = 'TRANSFER_APPROVED', 'Transfer Approved'
        TRANSFER_REJECTED = 'TRANSFER_REJECTED', 'Transfer Rejected'
        ESCALATION = 'ESCALATION', 'Escalated to Higher Authority'
        ESCALATION_RESOLVED = 'ESCALATION_RESOLVED', 'Escalation Resolved'
        DOCUMENT_UPLOADED = 'DOCUMENT_UPLOADED', 'Supporting Document Uploaded'
        REMARK_ADDED = 'REMARK_ADDED', 'Action Remark Recorded'
        DISPOSED = 'DISPOSED', 'Complaint Disposed & Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)
    responsible_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    responsible_bureau = models.ForeignKey(
        Bureau,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    remarks = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    related_document = models.ForeignKey(
        ComplaintDocument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Complaint Action'
        verbose_name_plural = 'Complaint Actions'

    def __str__(self):
        return f"{self.action_type} on {self.complaint.complaint_no} at {self.timestamp:%Y-%m-%d %H:%M}"

class ComplaintTransfer(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Destination Bureau Approval'
        APPROVED = 'APPROVED', 'Transfer Approved & Re-assigned'
        REJECTED = 'REJECTED', 'Transfer Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    source_bureau = models.ForeignKey(
        Bureau,
        on_delete=models.PROTECT,
        related_name='transfers_out'
    )
    destination_bureau = models.ForeignKey(
        Bureau,
        on_delete=models.PROTECT,
        related_name='transfers_in'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_transfers'
    )
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    approval_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='decided_transfers'
    )
    decision_timestamp = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Transfer of {self.complaint.complaint_no} from {self.source_bureau.code} to {self.destination_bureau.code}"

class ComplaintEscalation(models.Model):
    class Level(models.TextChoices):
        LEVEL_1_BUREAU_HEAD = 'LEVEL_1_BUREAU_HEAD', 'Level 1: Bureau Head Scrutiny'
        LEVEL_2_MEMBER_SECRETARY = 'LEVEL_2_MEMBER_SECRETARY', 'Level 2: Member Secretary'
        LEVEL_3_CHAIRMAN = 'LEVEL_3_CHAIRMAN', 'Level 3: Competent Authority / Chairman'

    class ResolutionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Under High-Level Review'
        REMANDED = 'REMANDED', 'Remanded with Instructions'
        RESOLVED = 'RESOLVED', 'Disposed by Competent Authority'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='escalations'
    )
    escalation_level = models.CharField(max_length=50, choices=Level.choices, default=Level.LEVEL_2_MEMBER_SECRETARY)
    reason = models.TextField()
    responsible_authority = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_escalations'
    )
    escalation_timestamp = models.DateTimeField(auto_now_add=True)
    resolution_status = models.CharField(
        max_length=30,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.PENDING
    )
    decision_remarks = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-escalation_timestamp']

    def __str__(self):
        return f"Escalation of {self.complaint.complaint_no} [{self.escalation_level}]"

class CaseRelationship(models.Model):
    class RelationType(models.TextChoices):
        SAME_INSTITUTION = 'SAME_INSTITUTION', 'Same Institution Activity'
        POTENTIALLY_RELATED = 'POTENTIALLY_RELATED', 'Potentially Related Issue'
        CONFIRMED_RELATED = 'CONFIRMED_RELATED', 'Confirmed Related Issue'
        DUPLICATE_REPORT = 'DUPLICATE_REPORT', 'Duplicate Grievance'
        SEPARATE_ISSUES = 'SEPARATE_ISSUES', 'Confirmed Distinct Issues'
        PARENT_CHILD = 'PARENT_CHILD', 'Parent Umbrella / Child Case'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='relationships_as_source'
    )
    target_complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='relationships_as_target'
    )
    relationship_type = models.CharField(max_length=40, choices=RelationType.choices)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('source_complaint', 'target_complaint', 'relationship_type')
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source_complaint=models.F('target_complaint')),
                name='case_relationship_no_self_link'
            )
        ]

    def __str__(self):
        return f"{self.source_complaint.complaint_no} <-> {self.target_complaint.complaint_no} ({self.relationship_type})"

class ComplaintSequence(models.Model):
    """
    PostgreSQL concurrency-safe atomic sequence tracker per bureau-year.
    Guarantees collision-free sequential numbering under simultaneous requests.
    """
    bureau_code = models.CharField(max_length=20, db_index=True)
    year = models.IntegerField(db_index=True)
    last_number = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Complaint Sequence Counter'
        verbose_name_plural = 'Complaint Sequence Counters'
        unique_together = ('bureau_code', 'year')

    def __str__(self):
        return f"{self.bureau_code}-{self.year}: {self.last_number}"

