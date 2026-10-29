import re
import uuid
from django.db import models
from apps.accounts.models import User

def normalize_text_key(text):
    if not text:
        return ''
    # Lowercase, replace non-alphanumeric with spaces, collapse spaces
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    return ' '.join(cleaned.split())

class Institution(models.Model):
    class InstitutionType(models.TextChoices):
        ENGINEERING = 'ENGINEERING', 'Engineering & Technology'
        MANAGEMENT = 'MANAGEMENT', 'Management / MBA / PGDM'
        PHARMACY = 'PHARMACY', 'Pharmacy'
        POLYTECHNIC = 'POLYTECHNIC', 'Polytechnic Diploma'
        ARCHITECTURE = 'ARCHITECTURE', 'Architecture & Planning'
        HOTEL_MGMT = 'HOTEL_MGMT', 'Hotel Management & Catering'
        OTHER = 'OTHER', 'Other Technical Institution'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active / Approved'
        UNDER_SCRUTINY = 'UNDER_SCRUTINY', 'Under Regulatory Scrutiny'
        APPROVAL_WITHHELD = 'APPROVAL_WITHHELD', 'Approval Withheld'
        CLOSED = 'CLOSED', 'Closed / De-affiliated'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aicte_permanent_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique AICTE Permanent Institution ID, e.g. 1-123456789"
    )
    name = models.CharField(max_length=255, db_index=True)
    normalized_name = models.CharField(max_length=255, db_index=True, blank=True)
    institution_type = models.CharField(
        max_length=50,
        choices=InstitutionType.choices,
        default=InstitutionType.ENGINEERING
    )
    address = models.TextField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    region = models.CharField(
        max_length=50,
        choices=User.Region.choices,
        db_index=True
    )
    pincode = models.CharField(max_length=10)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    operational_status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Institution'
        verbose_name_plural = 'Institutions'
        indexes = [
            models.Index(fields=['region', 'operational_status']),
            models.Index(fields=['state', 'district']),
        ]

    def __str__(self):
        return f"{self.name} [{self.aicte_permanent_id}]"

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_text_key(self.name)
        super().save(*args, **kwargs)
