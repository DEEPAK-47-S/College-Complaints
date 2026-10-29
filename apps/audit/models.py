import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_events'
    )
    actor_username = models.CharField(max_length=150, default='SYSTEM')
    event_type = models.CharField(max_length=60, db_index=True)
    entity_type = models.CharField(max_length=60, db_index=True)
    entity_id = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    change_summary = models.JSONField(default=dict)
    request_correlation_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Event'
        verbose_name_plural = 'Audit Events'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['event_type', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.actor_username} - {self.event_type} on {self.entity_type}:{self.entity_id}"

    def clean(self):
        if self.pk:
            # Prevent editing existing audit events
            orig = AuditEvent.objects.filter(pk=self.pk).first()
            if orig:
                raise ValidationError("Audit records are strictly immutable and cannot be updated.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit records are append-only and cannot be deleted.")
