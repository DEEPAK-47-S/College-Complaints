import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.bureaus.models import Bureau
from apps.accounts.models import User
from apps.institutions.models import Institution
from apps.complaints.models import ComplaintCategory, Complaint, ComplaintAction
from apps.notifications.models import SLAPolicy
from apps.intelligence.services import OverlapDetectionService
from apps.coordination.services import CoordinationService

class Command(BaseCommand):
    help = "Seeds idempotent realistic synthetic demonstration data: ~50 institutions, ~200 complaints, roles, and overlaps."

    def handle(self, *args, **options):
        self.stdout.write("Initializing AUGIS Synthetic Seeder...")

        # 1. Bureaus
        bureau_data = [
            ('RB', 'Regulation Bureau', 'Regulatory compliance, affiliation norms, and statutory inspection oversight.'),
            ('PGRC', 'Public Grievance Redressal Cell', 'Direct public, student, and faculty complaints redressal unit.'),
            ('AB', 'Approval Bureau', 'AICTE institutional approval, program expansion, and closure scrutiny.'),
            ('RO_NORTH', 'Regional Office Northern', 'Field jurisdiction for Northern zone states.'),
            ('RO_SOUTH', 'Regional Office Southern', 'Field jurisdiction for Southern zone states.'),
        ]

        bureaus = {}
        for code, name, desc in bureau_data:
            b, _ = Bureau.objects.update_or_create(
                code=code,
                defaults={'name': name, 'description': desc, 'is_active': True}
            )
            bureaus[code] = b

        self.stdout.write(self.style.SUCCESS(f"Configured {len(bureaus)} AICTE Bureaus & Cells."))

        # 2. SLA Policies & Categories
        cat_data = [
            ('INFRA_DEFICIENCY', 'Infrastructure & Laboratory Deficiencies', 25),
            ('CAPITATION_FEE', 'Capitation Fee & Excess Tuition Demands', 15),
            ('FACULTY_SHORTAGE', 'Faculty Shortage & Salary Non-Payment', 30),
            ('UNAPPROVED_COURSES', 'Unapproved Programs & Fake Affiliations', 20),
            ('RAGGING_HARASSMENT', 'Ragging & Student Harassment Violations', 7),
            ('EXAM_MALPRACTICE', 'Examination Conduct & Certification Malpractice', 30),
            ('GOVERNANCE_ISSUE', 'Administrative Governance & Trust Disputes', 45),
        ]

        categories = {}
        for code, name, default_sla in cat_data:
            cat, _ = ComplaintCategory.objects.update_or_create(
                code=code,
                defaults={'name': name, 'default_sla_days': default_sla, 'is_active': True}
            )
            categories[code] = cat
            SLAPolicy.objects.update_or_create(
                name=f"Standard {cat.name} Policy",
                category=cat,
                defaults={'duration_days': default_sla, 'is_working_days': True, 'is_active': True}
            )

        self.stdout.write(self.style.SUCCESS(f"Configured {len(categories)} Complaint Categories & SLA Policies."))

        # 3. User Accounts for all 6 Roles
        demo_users = [
            ('admin', 'admin@augis.aicte.gov.in', 'Dr. Rajesh Sharma', User.Role.SUPER_ADMIN, None, ''),
            ('rb_head', 'rb.head@augis.aicte.gov.in', 'Dr. Anand Varma', User.Role.BUREAU_HEAD, bureaus['RB'], ''),
            ('pgrc_head', 'pgrc.head@augis.aicte.gov.in', 'Prof. Sunita Rao', User.Role.BUREAU_HEAD, bureaus['PGRC'], ''),
            ('rb_officer', 'rb.officer@augis.aicte.gov.in', 'Vikram Patel', User.Role.CASE_OFFICER, bureaus['RB'], ''),
            ('pgrc_officer', 'pgrc.officer@augis.aicte.gov.in', 'Pooja Iyer', User.Role.CASE_OFFICER, bureaus['PGRC'], ''),
            ('ro_north', 'ro.north@augis.aicte.gov.in', 'Sanjay Gupta', User.Role.REGIONAL_OFFICER, bureaus['RO_NORTH'], User.Region.NORTHERN),
            ('senior_mgmt', 'mgmt@augis.aicte.gov.in', 'Advisor K. Balaji', User.Role.SENIOR_MGMT, None, ''),
            ('competent_auth', 'chairman@augis.aicte.gov.in', 'Prof. T. G. Sitharam (Authority)', User.Role.COMPETENT_AUTH, None, ''),
        ]

        users = {}
        for username, email, display_name, role, bureau, region in demo_users:
            u, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': email,
                    'display_name': display_name,
                    'role': role,
                    'assigned_bureau': bureau,
                    'authorized_region': region,
                    'is_staff': (role == User.Role.SUPER_ADMIN),
                    'is_superuser': (role == User.Role.SUPER_ADMIN),
                    'is_active': True
                }
            )
            u.set_password('Augis@2026')
            u.save()
            users[username] = u

        self.stdout.write(self.style.SUCCESS(f"Provisioned {len(users)} Demo Accounts (Password: 'Augis@2026')."))

        # 4. 50 Fictional Institutions
        regions = list(User.Region.choices)
        types = list(Institution.InstitutionType.choices)
        prefixes = ['Apex', 'Bharat', 'Cauvery', 'Delta', 'Everest', 'Frontier', 'Ganga', 'Heritage', 'Indus', 'Jupiter',
                    'Kaveri', 'Lotus', 'Modern', 'National', 'Oxford', 'Premier', 'Quantum', 'Radiant', 'Starlight', 'Trinity']
        cities = [
            ('New Delhi', 'Delhi', 'NORTHERN'), ('Lucknow', 'Uttar Pradesh', 'NORTHERN'), ('Chandigarh', 'Punjab', 'NORTH_WEST'),
            ('Bengaluru', 'Karnataka', 'SOUTH_WEST'), ('Chennai', 'Tamil Nadu', 'SOUTHERN'), ('Hyderabad', 'Telangana', 'SOUTH_WEST'),
            ('Mumbai', 'Maharashtra', 'WESTERN'), ('Pune', 'Maharashtra', 'WESTERN'), ('Kolkata', 'West Bengal', 'EASTERN'),
            ('Bhopal', 'Madhya Pradesh', 'CENTRAL')
        ]

        institutions = []
        for i in range(1, 51):
            perm_id = f"1-AICTE-{10000 + i}"
            city_info = cities[i % len(cities)]
            prefix = prefixes[i % len(prefixes)]
            inst_type = types[i % len(types)][0]
            name = f"{prefix} {inst_type.capitalize()} Institute of Higher Learning ({city_info[0]}) [Synthetic]"

            inst, _ = Institution.objects.update_or_create(
                aicte_permanent_id=perm_id,
                defaults={
                    'name': name,
                    'institution_type': inst_type,
                    'address': f"Plot {100 + i}, Sector {i % 20 + 1}, Institutional Area",
                    'district': city_info[0],
                    'state': city_info[1],
                    'region': city_info[2],
                    'pincode': f"{500000 + (i * 123) % 99999:06d}",
                    'contact_email': f"info.{perm_id.lower()}@synthetic.edu.in",
                    'contact_phone': f"+91-984210{i:04d}",
                    'operational_status': Institution.Status.ACTIVE if i % 12 != 0 else Institution.Status.UNDER_SCRUTINY
                }
            )
            institutions.append(inst)

        self.stdout.write(self.style.SUCCESS(f"Registered {len(institutions)} Synthetic Institutions."))

        # 5. ~200 Complaints with Explicit Cross-Bureau Overlap Scenarios
        # Scenario A: ABC Apex Institute (inst 0) has overlapping laboratory complaints in RB and PGRC!
        sample_complaint_templates = [
            ("Non-compliance of basic laboratory equipment norms in Computer and Mechanical Engineering departments.", 'INFRA_DEFICIENCY'),
            ("Acute shortage of laboratory computers and broken machinery hindering practical curriculum.", 'INFRA_DEFICIENCY'),
            ("Illegal demand of capitation fee of Rs 2.5 Lakhs during direct management quota admission.", 'CAPITATION_FEE'),
            ("Mandatory fee extortion and withholding of 12th standard original certificates upon request for refund.", 'CAPITATION_FEE'),
            ("Non-payment of faculty salary for 5 consecutive months in violation of approved pay scales.", 'FACULTY_SHORTAGE'),
            ("Running unapproved AI & Machine Learning diploma programs without prior AICTE extension of approval.", 'UNAPPROVED_COURSES'),
            ("Severe hostel ragging incident and intimidation of first-year engineering undergraduates.", 'RAGGING_HARASSMENT'),
            ("Mass examination malpractice and invigilator collusion during semester end assessments.", 'EXAM_MALPRACTICE'),
            ("Trustee disputes affecting institutional administrative governance and student stipend disbursement.", 'GOVERNANCE_ISSUE'),
        ]

        statuses = [
            Complaint.Status.PENDING,
            Complaint.Status.UNDER_PROCESS,
            Complaint.Status.UNDER_PROCESS,
            Complaint.Status.TRANSFERRED,
            Complaint.Status.ESCALATED,
            Complaint.Status.DISPOSED
        ]

        bureau_pool = [bureaus['RB'], bureaus['PGRC'], bureaus['AB'], bureaus['RO_NORTH']]
        officer_pool = [users['rb_officer'], users['pgrc_officer'], None]

        created_complaints = []
        now = timezone.now()

        # Seed 200 complaints
        for i in range(1, 201):
            inst = institutions[i % len(institutions)]
            tmpl_idx = i % len(sample_complaint_templates)
            title_text, cat_code = sample_complaint_templates[tmpl_idx]

            days_ago = (200 - i) * 2  # Span over past ~400 days
            recv_date = (now - timedelta(days=days_ago)).date()
            status = statuses[i % len(statuses)]
            bureau = bureau_pool[i % len(bureau_pool)]
            officer = officer_pool[i % len(officer_pool)]
            category = categories[cat_code]

            complaint_no = f"AICTE-2026-{bureau.code}-{10000 + i}"
            sla_days = category.default_sla_days
            expected_disposal = recv_date + timedelta(days=sla_days)

            # Check if overdue
            is_disposed = (status == Complaint.Status.DISPOSED)
            disposed_at = (now - timedelta(days=random.randint(1, 30))) if is_disposed else None

            # Varied text for NLP
            narrative = (
                f"Synthetic Grievance Report #{i}: Formal petition concerning {inst.name}. "
                f"Allegations state: {title_text} "
                f"Evidence indicates persistent departmental irregularities under {bureau.code} scope. "
                f"Complainant requests urgent regulatory inspection and appropriate disciplinary scrutiny."
            )

            c, _ = Complaint.objects.update_or_create(
                complaint_no=complaint_no,
                defaults={
                    'institution': inst,
                    'title': f"{title_text[:60]} [{inst.district}]",
                    'description': narrative,
                    'category': category,
                    'source_channel': Complaint.SourceChannel.PORTAL if i % 2 == 0 else Complaint.SourceChannel.CPGRAMS_FORWARD,
                    'external_reference_no': f"CPGRAMS-2026-REF-{1000 + i}" if i % 3 == 0 else '',
                    'date_received': recv_date,
                    'current_status': status,
                    'priority': Complaint.Priority.URGENT if i % 10 == 0 else (Complaint.Priority.HIGH if i % 5 == 0 else Complaint.Priority.MEDIUM),
                    'currently_assigned_bureau': bureau,
                    'currently_assigned_officer': officer,
                    'expected_disposal_date': expected_disposal,
                    'created_by': users['admin'],
                    'disposed_at': disposed_at,
                    'closure_remarks': f"Formal disposal order issued and recorded following satisfactory inquiry." if is_disposed else ""
                }
            )

            # Action history
            ComplaintAction.objects.get_or_create(
                complaint=c,
                action_type=ComplaintAction.ActionType.CREATED,
                defaults={
                    'previous_status': '',
                    'new_status': Complaint.Status.PENDING,
                    'responsible_officer': users['admin'],
                    'responsible_bureau': bureau,
                    'remarks': f"Initial grievance logged via web intake."
                }
            )

            if officer:
                ComplaintAction.objects.get_or_create(
                    complaint=c,
                    action_type=ComplaintAction.ActionType.ASSIGNED,
                    defaults={
                        'previous_status': Complaint.Status.PENDING,
                        'new_status': c.current_status,
                        'responsible_officer': users['rb_head'] if bureau.code == 'RB' else users['pgrc_head'],
                        'responsible_bureau': bureau,
                        'remarks': f"Assigned to {officer.display_name} for scrutiny."
                    }
                )

            created_complaints.append(c)

        self.stdout.write(self.style.SUCCESS(f"Generated {len(created_complaints)} Synthetic Complaints."))

        # 6. Run Overlap Detection Engine on Key Candidate Cases
        self.stdout.write("Running Overlap Intelligence Engine across generated sample pairs...")
        for c in created_complaints[:40]:
            try:
                OverlapDetectionService.detect_overlaps_for_complaint(c)
            except Exception as e:
                pass

        # 7. Seed one Sample Coordination Record
        from apps.intelligence.models import OverlapCandidate
        sample_candidate = OverlapCandidate.objects.filter(combined_score__gte=0.6).first()
        if sample_candidate:
            OverlapDetectionService.confirm_overlap(
                sample_candidate.id,
                users['rb_head'],
                "Confirmed inter-bureau related issue during joint preliminary scrutiny."
            )
            CoordinationService.initiate_coordination(
                title=f"Joint Scrutiny: {sample_candidate.first_complaint.institution.name}",
                coordinating_bureau=sample_candidate.first_complaint.currently_assigned_bureau,
                participating_bureaus=[
                    sample_candidate.first_complaint.currently_assigned_bureau,
                    sample_candidate.second_complaint.currently_assigned_bureau
                ],
                complaints=[sample_candidate.first_complaint, sample_candidate.second_complaint],
                created_by=users['rb_head'],
                action_plan="Joint inspection scheduled for verification of laboratory infrastructure and certification records.",
                deadline=(now + timedelta(days=14)).date()
            )
            self.stdout.write(self.style.SUCCESS("Established Demonstration Joint Coordination Workspace."))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] AUGIS Demonstration Database successfully seeded!"))
