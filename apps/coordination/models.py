import uuid
from django.db import models
from django.conf import settings
from apps.bureaus.models import Bureau
from apps.complaints.models import Complaint

class CoordinationRecord(models.Model):
    class Status(models.TextChoices):
        INITIATED = 'INITIATED', 'Joint Coordination Initiated'
        IN_PROGRESS = 'IN_PROGRESS', 'Active Joint Investigation'
        RESOLVED = 'RESOLVED', 'Consensus Order Formulated'
        CLOSED = 'CLOSED', 'Coordination Concluded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coordination_no = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="e.g. COORD-2026-00042"
    )
    title = models.CharField(max_length=255)
    coordinating_bureau = models.ForeignKey(
        Bureau,
        on_delete=models.PROTECT,
        related_name='coordinated_records',
        help_text="Designated Lead Coordinating Bureau"
    )
    participating_bureaus = models.ManyToManyField(
        Bureau,
        related_name='participating_coordinations'
    )
    related_complaints = models.ManyToManyField(
        Complaint,
        related_name='coordination_records'
    )
    responsible_officers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_coordinations',
        blank=True
    )
    coordination_status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.INITIATED,
        db_index=True
    )
    action_plan = models.TextField(blank=True, help_text="Joint inspection or agreed steps")
    decision_summary = models.TextField(blank=True, help_text="Agreed coordinated regulatory stance")
    next_action = models.CharField(max_length=255, blank=True)
    deadline = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='initiated_coordinations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Coordination Record'
        verbose_name_plural = 'Coordination Records'

    def __str__(self):
        return f"{self.coordination_no} - {self.title}"

class CoordinationNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coordination = models.ForeignKey(
        CoordinationRecord,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    author_bureau = models.ForeignKey(
        Bureau,
        on_delete=models.PROTECT
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Note by {self.author.display_name} ({self.author_bureau.code}) on {self.coordination.coordination_no}"

class CoordinationSequence(models.Model):
    """
    PostgreSQL concurrency-safe atomic sequence tracker per year.
    Guarantees collision-free sequential numbering under simultaneous requests.
    """
    year = models.IntegerField(unique=True, db_index=True)
    last_number = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Coordination Sequence Counter'
        verbose_name_plural = 'Coordination Sequence Counters'

    def __str__(self):
        return f"{self.year}: {self.last_number}"

