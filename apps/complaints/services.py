import hashlib
import os
import uuid
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Complaint, ComplaintDocument, ComplaintAction, ComplaintSequence
from apps.audit.services import log_audit_event

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

import time
from django.db import transaction, OperationalError

def generate_complaint_number(bureau_code, year=None):
    """
    Concurrency-safe complaint number generator: AICTE-{YEAR}-{BUREAU_CODE}-{SEQ:05d}
    Uses dedicated atomic ComplaintSequence counter row locked with select_for_update().
    Guarantees zero collision under true simultaneous transactions.
    """
    if not year:
        year = timezone.now().year
    
    clean_code = (bureau_code or 'GEN').upper().replace(' ', '')
    prefix = f"AICTE-{year}-{clean_code}-"
    
    max_retries = 15
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                seq_obj, _ = ComplaintSequence.objects.select_for_update().get_or_create(
                    bureau_code=clean_code,
                    year=year,
                    defaults={'last_number': 0}
                )
                if seq_obj.last_number == 0:
                    existing_count = Complaint.objects.filter(complaint_no__startswith=prefix).count()
                    seq_obj.last_number = existing_count

                seq_obj.last_number += 1
                complaint_no = f"{prefix}{seq_obj.last_number:05d}"
                
                while Complaint.objects.filter(complaint_no=complaint_no).exists():
                    seq_obj.last_number += 1
                    complaint_no = f"{prefix}{seq_obj.last_number:05d}"

                seq_obj.save()
                return complaint_no
        except OperationalError:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.03 * (attempt + 1))

def validate_and_save_document(complaint, file_obj, user, classification=ComplaintDocument.Classification.INTERNAL_ONLY):
    """
    Validates uploaded file against extension whitelist and size caps,
    computes SHA-256 hash, and stores in private vault.
    """
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}")

    if file_obj.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(f"File size ({file_obj.size / 1024 / 1024:.1f} MB) exceeds maximum allowed limit of 10 MB.")

    # Magic byte header signature validation
    file_obj.seek(0)
    header = file_obj.read(16)
    file_obj.seek(0)

    if ext == '.pdf' and not header.startswith(b'%PDF-'):
        raise ValidationError("Invalid file signature: Content is not a valid PDF document.")
    elif ext == '.png' and not header.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValidationError("Invalid file signature: Content is not a valid PNG image.")
    elif ext in ['.jpg', '.jpeg'] and not header.startswith(b'\xff\xd8\xff'):
        raise ValidationError("Invalid file signature: Content is not a valid JPEG image.")

    # Calculate SHA256
    sha256 = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256.update(chunk)
    checksum = sha256.hexdigest()

    # Store with randomized safe filename
    stored_name = f"{uuid.uuid4()}{ext}"
    doc = ComplaintDocument.objects.create(
        complaint=complaint,
        file=file_obj,
        original_filename=file_obj.name,
        stored_filename=stored_name,
        file_type=ext.lstrip('.'),
        file_size=file_obj.size,
        uploader=user,
        visibility_classification=classification,
        checksum=checksum
    )

    # Log action
    ComplaintAction.objects.create(
        complaint=complaint,
        action_type=ComplaintAction.ActionType.DOCUMENT_UPLOADED,
        previous_status=complaint.current_status,
        new_status=complaint.current_status,
        responsible_officer=user,
        responsible_bureau=complaint.currently_assigned_bureau,
        remarks=f"Document uploaded: {file_obj.name} (SHA-256: {checksum[:8]}...)",
        related_document=doc
    )

    log_audit_event(
        actor=user,
        event_type="DOCUMENT_UPLOADED",
        entity_name="ComplaintDocument",
        entity_id=str(doc.id),
        change_summary={"filename": file_obj.name, "checksum": checksum, "complaint_no": complaint.complaint_no}
    )

    return doc

def create_complaint(
    institution,
    title,
    description,
    category,
    bureau,
    source_channel,
    created_by,
    priority='MEDIUM',
    external_reference_no='',
    assigned_officer=None
):
    """
    Creates a new complaint inside an atomic transaction, calculates initial SLA,
    records CREATED action, and triggers the Overlap Detection Engine.
    """
    with transaction.atomic():
        complaint_no = generate_complaint_number(bureau.code)
        
        # Calculate expected disposal date from category default SLA
        sla_days = category.default_sla_days if category else 30
        expected_disposal = timezone.now().date() + timedelta(days=sla_days)

        complaint = Complaint.objects.create(
            complaint_no=complaint_no,
            institution=institution,
            title=title,
            description=description,
            category=category,
            source_channel=source_channel,
            external_reference_no=external_reference_no,
            date_received=timezone.now().date(),
            current_status=Complaint.Status.PENDING,
            priority=priority,
            currently_assigned_bureau=bureau,
            currently_assigned_officer=assigned_officer,
            expected_disposal_date=expected_disposal,
            created_by=created_by
        )

        ComplaintAction.objects.create(
            complaint=complaint,
            action_type=ComplaintAction.ActionType.CREATED,
            previous_status='',
            new_status=Complaint.Status.PENDING,
            responsible_officer=created_by,
            responsible_bureau=bureau,
            remarks=f"Complaint registered and assigned to {bureau.code}."
        )

        log_audit_event(
            actor=created_by,
            event_type="COMPLAINT_REGISTERED",
            entity_name="Complaint",
            entity_id=str(complaint.id),
            change_summary={
                "complaint_no": complaint.complaint_no,
                "institution": institution.name,
                "bureau": bureau.code,
                "priority": priority
            }
        )

        # Trigger overlap detection engine after transaction commit
        def run_overlap_detection():
            try:
                from apps.intelligence.services import OverlapDetectionService
                OverlapDetectionService.detect_overlaps_for_complaint(complaint)
            except Exception as e:
                import logging
                logging.getLogger('augis.intelligence').error(f"Overlap detection non-blocking failure: {e}")

        transaction.on_commit(run_overlap_detection)

        return complaint
