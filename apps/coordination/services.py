from django.db import transaction
from django.utils import timezone
from .models import CoordinationRecord, CoordinationNote, CoordinationSequence
from apps.audit.services import log_audit_event

import time
from django.db import transaction, OperationalError

def generate_coordination_number():
    year = timezone.now().year
    prefix = f"COORD-{year}-"
    max_retries = 15
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                seq_obj, _ = CoordinationSequence.objects.select_for_update().get_or_create(
                    year=year,
                    defaults={'last_number': 0}
                )
                if seq_obj.last_number == 0:
                    existing_count = CoordinationRecord.objects.filter(coordination_no__startswith=prefix).count()
                    seq_obj.last_number = existing_count

                seq_obj.last_number += 1
                coord_no = f"{prefix}{seq_obj.last_number:05d}"
                while CoordinationRecord.objects.filter(coordination_no=coord_no).exists():
                    seq_obj.last_number += 1
                    coord_no = f"{prefix}{seq_obj.last_number:05d}"

                seq_obj.save()
                return coord_no
        except OperationalError:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.03 * (attempt + 1))

class CoordinationService:
    @staticmethod
    def initiate_coordination(
        title,
        coordinating_bureau,
        participating_bureaus,
        complaints,
        created_by,
        action_plan='',
        deadline=None,
        responsible_officers=None
    ):
        with transaction.atomic():
            coord_no = generate_coordination_number()
            coord = CoordinationRecord.objects.create(
                coordination_no=coord_no,
                title=title,
                coordinating_bureau=coordinating_bureau,
                action_plan=action_plan,
                deadline=deadline,
                created_by=created_by,
                coordination_status=CoordinationRecord.Status.INITIATED
            )
            coord.participating_bureaus.set(participating_bureaus)
            coord.related_complaints.set(complaints)
            if responsible_officers:
                coord.responsible_officers.set(responsible_officers)

            # Record initial note
            bureau = created_by.assigned_bureau or coordinating_bureau
            CoordinationNote.objects.create(
                coordination=coord,
                author=created_by,
                author_bureau=bureau,
                note=f"Joint inter-bureau coordination initiated. Lead: {coordinating_bureau.code}."
            )

            log_audit_event(
                actor=created_by,
                event_type="COORDINATION_INITIATED",
                entity_name="CoordinationRecord",
                entity_id=str(coord.id),
                change_summary={
                    "coordination_no": coord.coordination_no,
                    "lead_bureau": coordinating_bureau.code,
                    "participating_count": len(participating_bureaus),
                    "complaints_count": len(complaints)
                }
            )

        return coord

    @staticmethod
    def add_note(coordination, author, note):
        bureau = author.assigned_bureau or coordination.coordinating_bureau
        return CoordinationNote.objects.create(
            coordination=coordination,
            author=author,
            author_bureau=bureau,
            note=note
        )

    @staticmethod
    def update_coordination_status(coordination, new_status, actor, decision_summary=''):
        with transaction.atomic():
            old_status = coordination.coordination_status
            coordination.coordination_status = new_status
            if decision_summary:
                coordination.decision_summary = decision_summary
            coordination.save()

            bureau = actor.assigned_bureau or coordination.coordinating_bureau
            CoordinationNote.objects.create(
                coordination=coordination,
                author=actor,
                author_bureau=bureau,
                note=f"Status changed from {old_status} to {new_status}. {decision_summary}".strip()
            )

            log_audit_event(
                actor=actor,
                event_type="COORDINATION_STATUS_UPDATE",
                entity_name="CoordinationRecord",
                entity_id=str(coordination.id),
                change_summary={
                    "coordination_no": coordination.coordination_no,
                    "old_status": old_status,
                    "new_status": new_status
                }
            )
        return coordination
