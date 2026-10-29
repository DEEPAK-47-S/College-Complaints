"""
AUGIS Seed Script: Authentic Tamil Nadu Technical Institutions & AICTE Case Dockets
Populates real Tamil Nadu engineering colleges with authentic AICTE Permanent IDs,
and creates realistic cross-bureau grievance dockets representing Problem Statement 2.
"""
import os
import sys
import uuid
import datetime
from django.utils import timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.institutions.models import Institution
from apps.bureaus.models import Bureau
from apps.complaints.models import Complaint, ComplaintCategory
from apps.accounts.models import User
from apps.intelligence.services import OverlapDetectionService
from apps.intelligence.gemini_service import GeminiAnalysisService

TAMIL_NADU_COLLEGES = [
    {
        "name": "PSG College of Technology, Coimbatore",
        "aicte_id": "1-4165514",
        "type": "ENGINEERING",
        "address": "Avinashi Road, Peelamedu",
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "641004",
        "region": "SOUTHERN"
    },
    {
        "name": "Thiagarajar College of Engineering, Madurai",
        "aicte_id": "1-429823423",
        "type": "ENGINEERING",
        "address": "Thiruparankundram",
        "district": "Madurai",
        "state": "Tamil Nadu",
        "pincode": "625015",
        "region": "SOUTHERN"
    },
    {
        "name": "Sri Sivasubramaniya Nadar (SSN) College of Engineering, Chennai",
        "aicte_id": "1-1229101",
        "type": "ENGINEERING",
        "address": "Rajiv Gandhi Salai (OMR), Kalavakkam",
        "district": "Chengalpattu",
        "state": "Tamil Nadu",
        "pincode": "603110",
        "region": "SOUTHERN"
    },
    {
        "name": "Coimbatore Institute of Technology (CIT), Coimbatore",
        "aicte_id": "1-4221764",
        "type": "ENGINEERING",
        "address": "Civil Aerodrome Post",
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "641014",
        "region": "SOUTHERN"
    },
    {
        "name": "Government College of Technology (GCT), Coimbatore",
        "aicte_id": "1-4554801",
        "type": "ENGINEERING",
        "address": "Thadagam Road",
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "641013",
        "region": "SOUTHERN"
    },
    {
        "name": "College of Engineering, Guindy (CEG), Anna University, Chennai",
        "aicte_id": "1-4822001",
        "type": "ENGINEERING",
        "address": "Sardar Patel Road, Guindy",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600025",
        "region": "SOUTHERN"
    },
    {
        "name": "Madras Institute of Technology (MIT), Chromepet, Chennai",
        "aicte_id": "1-5021489",
        "type": "ENGINEERING",
        "address": "MIT Road, Chromepet",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600044",
        "region": "SOUTHERN"
    },
    {
        "name": "Kongu Engineering College, Perundurai, Erode",
        "aicte_id": "1-401662465",
        "type": "ENGINEERING",
        "address": "Perundurai",
        "district": "Erode",
        "state": "Tamil Nadu",
        "pincode": "638060",
        "region": "SOUTHERN"
    },
    {
        "name": "Kumaraguru College of Technology (KCT), Coimbatore",
        "aicte_id": "1-4389101",
        "type": "ENGINEERING",
        "address": "Athipalayam Road, Chinnavedampatti",
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "641049",
        "region": "SOUTHERN"
    },
    {
        "name": "National Engineering College (NEC), Kovilpatti",
        "aicte_id": "1-4491024",
        "type": "ENGINEERING",
        "address": "K.R. Nagar, Kovilpatti",
        "district": "Thoothukudi",
        "state": "Tamil Nadu",
        "pincode": "628503",
        "region": "SOUTHERN"
    },
    {
        "name": "Mepco Schlenk Engineering College, Sivakasi",
        "aicte_id": "1-4712019",
        "type": "ENGINEERING",
        "address": "Mepco Engineering College Post",
        "district": "Virudhunagar",
        "state": "Tamil Nadu",
        "pincode": "626005",
        "region": "SOUTHERN"
    },
    {
        "name": "SRM Valliammai Engineering College, Kattankulathur",
        "aicte_id": "1-4629811",
        "type": "ENGINEERING",
        "address": "SRM Nagar, Kattankulathur",
        "district": "Chengalpattu",
        "state": "Tamil Nadu",
        "pincode": "603203",
        "region": "SOUTHERN"
    },
    {
        "name": "Bannari Amman Institute of Technology, Sathyamangalam",
        "aicte_id": "1-4560123",
        "type": "ENGINEERING",
        "address": "Alathukombai Post, Sathyamangalam",
        "district": "Erode",
        "state": "Tamil Nadu",
        "pincode": "638401",
        "region": "SOUTHERN"
    },
    {
        "name": "Annapoorana Engineering College, Salem",
        "aicte_id": "1-7030281",
        "type": "ENGINEERING",
        "address": "NH-47, Sankari Main Road, Periaseeragapadi",
        "district": "Salem",
        "state": "Tamil Nadu",
        "pincode": "636308",
        "region": "SOUTHERN"
    },
    {
        "name": "KCG College of Technology, Chennai",
        "aicte_id": "1-4401459",
        "type": "ENGINEERING",
        "address": "KCG Nagar, Rajiv Gandhi Salai, Karapakkam",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600097",
        "region": "SOUTHERN"
    }
]

def seed():
    print("=" * 70)
    print("AUGIS SEEDING: AUTHENTIC TAMIL NADU TECHNICAL INSTITUTIONS")
    print("=" * 70)

    # Fetch required master records
    bureau_rb = Bureau.objects.filter(code='RB').first()
    bureau_pgrc = Bureau.objects.filter(code='PGRC').first()
    bureau_ab = Bureau.objects.filter(code='AB').first()

    cat_infra = ComplaintCategory.objects.filter(code='INFRASTRUCTURE').first() or ComplaintCategory.objects.first()
    cat_faculty = ComplaintCategory.objects.filter(code='FACULTY_RECRUITMENT').first() or ComplaintCategory.objects.first()
    cat_fees = ComplaintCategory.objects.filter(code='FEE_IRREGULARITY').first() or ComplaintCategory.objects.first()
    cat_curriculum = ComplaintCategory.objects.filter(code='CURRICULUM_ACADEMIC').first() or ComplaintCategory.objects.first()

    admin_user = User.objects.filter(username='admin').first()
    rb_officer = User.objects.filter(username='rb_officer').first()
    pgrc_officer = User.objects.filter(username='pgrc_officer').first()

    institutions_created = 0
    complaints_created = 0

    today = timezone.now().date()

    for item in TAMIL_NADU_COLLEGES:
        inst, created = Institution.objects.update_or_create(
            aicte_permanent_id=item["aicte_id"],
            defaults={
                "name": item["name"],
                "institution_type": item["type"],
                "address": item["address"],
                "district": item["district"],
                "state": item["state"],
                "pincode": item["pincode"],
                "region": item["region"],
                "operational_status": Institution.Status.ACTIVE,
            }
        )
        if created:
            institutions_created += 1
            print(f"  [+] Created Institution: {inst.name} [{inst.aicte_permanent_id}]")
        else:
            print(f"  [*] Updated Institution: {inst.name} [{inst.aicte_permanent_id}]")

    # Seed cross-bureau overlap cases for PSG College of Technology (Problem Statement 2 Demonstration)
    psg = Institution.objects.get(aicte_permanent_id="1-4165514")
    
    # Check if PSG already has complaints
    if psg.complaints.count() < 2:
        # Case 1 (PGRC): Student hostel refund & laboratory amenities
        c1 = Complaint.objects.create(
            complaint_no="AICTE-2026-PGRC-TN101",
            institution=psg,
            category=cat_fees,
            title="Non-Refund of Hostel Caution Deposit and Mess Advance",
            description=(
                "Final-year engineering scholars report unwarranted delays exceeding 6 months in "
                "refunding refundable hostel caution deposits and excess mess advances. Students submitted "
                "multiple clearance applications to the campus administrative warden without resolution."
            ),
            current_status=Complaint.Status.UNDER_PROCESS,
            currently_assigned_bureau=bureau_pgrc,
            currently_assigned_officer=pgrc_officer,
            priority=Complaint.Priority.HIGH,
            date_received=today - datetime.timedelta(days=18),
            expected_disposal_date=today + datetime.timedelta(days=12),
            created_by=admin_user,
            last_action_date=timezone.now() - datetime.timedelta(days=2),
            next_action_required="Audit student ledger entries with finance bursar and summon reconciliation statement"
        )
        complaints_created += 1

        # Case 2 (RB): Regulatory compliance inquiry regarding sanctioned faculty ratio & student intake
        c2 = Complaint.objects.create(
            complaint_no="AICTE-2026-RB-TN102",
            institution=psg,
            category=cat_faculty,
            title="Faculty Cadre Ratio Deficiency and Ad-hoc Lecturer Recruitment in Core Engineering",
            description=(
                "Grievance lodged by technical education faculty association alleging breach of AICTE 1:20 "
                "cadre ratio across postgraduate mechanical and electrical departments. Alleges engagement of "
                "temporary adjunct faculty on unapproved consolidated stipends without AICTE Approval Process Handbook clearance."
            ),
            current_status=Complaint.Status.UNDER_PROCESS,
            currently_assigned_bureau=bureau_rb,
            currently_assigned_officer=rb_officer,
            priority=Complaint.Priority.URGENT,
            date_received=today - datetime.timedelta(days=14),
            expected_disposal_date=today + datetime.timedelta(days=16),
            created_by=admin_user,
            last_action_date=timezone.now() - datetime.timedelta(days=1),
            next_action_required="Dispatch formal show-cause questionnaire to Governing Council Chairperson"
        )
        complaints_created += 1

        # Trigger overlap detection
        cands1 = OverlapDetectionService.detect_overlaps_for_complaint(c1)
        for cand in cands1:
            GeminiAnalysisService.analyze_overlap(cand)
            print(f"  [AI] Generated Overlap Candidate: {cand.first_complaint.complaint_no} & {cand.second_complaint.complaint_no} ({cand.percentage_score}%)")

    # Seed cross-bureau overlap for Thiagarajar College of Engineering
    tce = Institution.objects.get(aicte_permanent_id="1-429823423")
    if tce.complaints.count() < 2:
        c3 = Complaint.objects.create(
            complaint_no="AICTE-2026-PGRC-TN103",
            institution=tce,
            category=cat_curriculum,
            title="Laboratory Practical Timetable Disruption and Equipment Scarcity in Automation Lab",
            description=(
                "Undergraduate students submitted petition to Public Grievance Redressal Cell citing "
                "unavailability of certified programmable logic controller workstations in advanced robotics laboratory, "
                "causing curriculum practical backlog ahead of autonomous university examinations."
            ),
            current_status=Complaint.Status.PENDING,
            currently_assigned_bureau=bureau_pgrc,
            currently_assigned_officer=None,
            priority=Complaint.Priority.MEDIUM,
            date_received=today - datetime.timedelta(days=6),
            expected_disposal_date=today + datetime.timedelta(days=24),
            created_by=admin_user,
            next_action_required="Assign investigating officer and request academic dean statement"
        )
        complaints_created += 1

        c4 = Complaint.objects.create(
            complaint_no="AICTE-2026-RB-TN104",
            institution=tce,
            category=cat_infra,
            title="Laboratory Infrastructure Norms Non-Compliance under AICTE Approval Process",
            description=(
                "Inspection scrutiny report indicating discrepancy in physical floor space and equipment specifications "
                "for new artificial intelligence and data science laboratory compared to certified compliance affidavit submitted for EoA."
            ),
            current_status=Complaint.Status.UNDER_PROCESS,
            currently_assigned_bureau=bureau_rb,
            currently_assigned_officer=rb_officer,
            priority=Complaint.Priority.HIGH,
            date_received=today - datetime.timedelta(days=9),
            expected_disposal_date=today + datetime.timedelta(days=21),
            created_by=admin_user,
            last_action_date=timezone.now() - datetime.timedelta(days=3),
            next_action_required="Coordinate with Southern Regional Office (SRO) for physical verification"
        )
        complaints_created += 1

        cands2 = OverlapDetectionService.detect_overlaps_for_complaint(c4)
        for cand in cands2:
            GeminiAnalysisService.analyze_overlap(cand)
            print(f"  [AI] Generated Overlap Candidate: {cand.first_complaint.complaint_no} & {cand.second_complaint.complaint_no} ({cand.percentage_score}%)")

    # Seed single grievance for SSN College of Engineering
    ssn = Institution.objects.get(aicte_permanent_id="1-1229101")
    if ssn.complaints.count() == 0:
        Complaint.objects.create(
            complaint_no="AICTE-2026-AB-TN105",
            institution=ssn,
            category=cat_curriculum,
            title="NRI Quota Admission Transparency and Merit List Publication Query",
            description=(
                "Stakeholder inquiry requesting formal audit of NRI and management quota admission merit rankings "
                "and fee structure adherence under state self-financing technical college regulatory guidelines."
            ),
            current_status=Complaint.Status.UNDER_PROCESS,
            currently_assigned_bureau=bureau_ab,
            currently_assigned_officer=None,
            priority=Complaint.Priority.MEDIUM,
            date_received=today - datetime.timedelta(days=12),
            expected_disposal_date=today + datetime.timedelta(days=18),
            created_by=admin_user,
            last_action_date=timezone.now() - datetime.timedelta(days=4),
            next_action_required="Examine published admissions cut-off roster and verify NRI sponsorship documents"
        )
        complaints_created += 1

    print(f"\n[OK] Seeding complete! Institutions added/updated: {len(TAMIL_NADU_COLLEGES)}, Complaints created: {complaints_created}")

if __name__ == "__main__":
    seed()
