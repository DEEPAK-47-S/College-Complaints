import uuid
from django.db import models
from django.conf import settings
from apps.bureaus.models import Bureau
from apps.complaints.models import ComplaintCategory, Complaint

class SLAPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, help_text="e.g. Standard 30-Day Resolution Policy")
    category = models.ForeignKey(
        ComplaintCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sla_policies'
    )
    applicable_bureau = models.ForeignKey(
        Bureau,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sla_policies'
    )
    priority = models.CharField(
        max_length=20,
        choices=[('ALL', 'All Priorities')] + list(Complaint.Priority.choices),
        default='ALL'
    )
    duration_days = models.PositiveIntegerField(default=30)
    is_working_days = models.BooleanField(
        default=True,
        help_text="Exclude weekends and gazetted holidays from SLA calculations"
    )
    escalation_threshold_days = models.PositiveIntegerField(
        default=5,
        help_text="Days prior to breach when warning alerts trigger"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SLA Policy'
        verbose_name_plural = 'SLA Policies'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.duration_days} days)"

class Notification(models.Model):
    class Type(models.TextChoices):
        OVERDUE_ALERT = 'OVERDUE_ALERT', 'SLA Overdue Warning'
        APPROACHING_SLA = 'APPROACHING_SLA', 'Approaching Resolution Deadline'
        OVERLAP_ALERT = 'OVERLAP_ALERT', 'Cross-Bureau Overlap Detected'
        DUPLICATE_ALERT = 'DUPLICATE_ALERT', 'Duplicate Complaint Detected'
        PENDING_REMINDER = 'PENDING_REMINDER', 'Pending Case Ageing Reminder'
        COORDINATION_UPDATE = 'COORDINATION_UPDATE', 'Joint Coordination Update'
        ASSIGNMENT = 'ASSIGNMENT', 'Case Assignment'
        TRANSFER = 'TRANSFER', 'Transfer Notification'
        ESCALATION = 'ESCALATION', 'Escalation Notice'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=40, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_complaint = models.ForeignKey(
        Complaint,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications'
    )
    related_coordination = models.ForeignKey(
        'coordination.CoordinationRecord',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications'
    )
    event_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Deterministic idempotency key preventing duplicate alerts"
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.notification_type}] {self.title} for {self.recipient.username}"
