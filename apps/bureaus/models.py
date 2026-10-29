import uuid
from django.db import models

class Bureau(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, help_text="e.g. RB, PGRC, RO_NORTH")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Bureau / Cell'
        verbose_name_plural = 'Bureaus & Cells'

    def __str__(self):
        return f"{self.code} - {self.name}"
