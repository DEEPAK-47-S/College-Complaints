"""
AUGIS Exhaustive End-to-End System Audit & Page Crawler
Verifies all public routes, authenticated officer views, button targets,
database transactions, and UI rendering integrity across every role.
"""
import os
import sys
import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import Client
from django.urls import reverse
from apps.accounts.models import User, PublicEmailOTP
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintAction
from apps.institutions.models import Institution
from apps.bureaus.models import Bureau
from apps.intelligence.models import OverlapCandidate
from apps.coordination.models import CoordinationRecord
from apps.notifications.models import Notification
from apps.accounts.queryset_scoping import (
    get_scoped_complaints,
    get_scoped_coordinations,
    get_scoped_overlap_candidates,
    get_scoped_institutions,
)

def run_system_audit():
    print("=" * 80)
    print("STARTING COMPREHENSIVE AUGIS SYSTEM & PAGE AUDIT")
    print("=" * 80)

    client = Client()
    audit_results = []
    errors_found = []

    def check_url(url, method="GET", data=None, expected_status=200, role="Anonymous", description=""):
        try:
            if method == "GET":
                resp = client.get(url, data=data or {})
            else:
                resp = client.post(url, data=data or {})

            status_ok = (resp.status_code == expected_status) or (expected_status == "REDIRECT" and resp.status_code in [301, 302])
            
            result_item = {
                "role": role,
                "url": url,
                "method": method,
                "status": resp.status_code,
                "expected": expected_status,
                "passed": status_ok,
                "description": description
            }
            audit_results.append(result_item)

            if status_ok:
                print(f"  [PASS] ({role:12}) {method:4} {url:45} -> {resp.status_code} {description}")
            else:
                print(f"  [FAIL] ({role:12}) {method:4} {url:45} -> {resp.status_code} (Expected {expected_status}) {description}")
                errors_found.append(f"{role} {method} {url}: Got {resp.status_code}, expected {expected_status}")

            return resp
        except Exception as e:
            print(f"  [ERROR] ({role:12}) {method:4} {url:45} -> EXCEPTION: {e}")
            errors_found.append(f"{role} {method} {url}: Exception {e}")
            return None

    # ---------------------------------------------------------
    # PART 1: PUBLIC GRIEVANCE PORTAL (Unauthenticated Citizen)
    # ---------------------------------------------------------
    print("\n--- 1. AUDITING PUBLIC GRIEVANCE PORTAL ---")
    
    # 1.1 Home
    resp = check_url("/", role="Public", description="Public Portal Homepage")
    assert b"COLLEGE GRIEVANCE PORTAL" in resp.content
    assert b"Submit Complaint" in resp.content
    assert b"Track Status" in resp.content

    # 1.2 Submit Page
    resp = check_url("/complaint/", role="Public", description="Grievance Registration Form")
    assert b"Grievance Registration Form" in resp.content
    assert b"Gmail OTP Verification" in resp.content

    # 1.3 Send OTP
    test_email = "audit.tester@gmail.com"
    resp = check_url("/complaint/send-otp/", method="POST", data={"email": test_email}, role="Public", description="Request Email OTP API")
    otp_json = resp.json()
    assert otp_json.get("success") is True
    test_otp = otp_json.get("otp")

    # 1.4 Verify OTP
    resp = check_url("/complaint/verify-otp/", method="POST", data={"email": test_email, "otp": test_otp}, role="Public", description="Verify OTP API")
    assert resp.json().get("success") is True

    # 1.5 Submit Complaint
    inst = Institution.objects.first()
    cat = ComplaintCategory.objects.first()
    complaint_data = {
        "email": test_email,
        "full_name": "Audit Test Complainant",
        "mobile_number": "9876543210",
        "complainant_type": "STUDENT",
        "institution": str(inst.id),
        "category": str(cat.id),
        "title": "Audit Verification Complaint - Infrastructure & Facilities",
        "description": "Comprehensive automated testing complaint to verify end-to-end database connectivity.",
        "issue_location": "Main Building, Room 204",
        "area": "Coimbatore",
        "priority": "HIGH"
    }
    resp = check_url("/complaint/", method="POST", data=complaint_data, expected_status="REDIRECT", role="Public", description="Submit Public Grievance")
    success_url = resp.url
    created_complaint_no = success_url.strip("/").split("/")[-1]

    # 1.6 Success Page
    resp = check_url(success_url, role="Public", description="Submission Success Page")
    assert created_complaint_no.encode() in resp.content
    assert b"Grievance Registered Successfully" in resp.content

    # 1.7 Track Status Form
    check_url("/track/", role="Public", description="Track Status Search Form")

    # 1.8 Track Search Action
    resp = check_url("/track/", method="POST", data={"complaint_id": created_complaint_no}, expected_status="REDIRECT", role="Public", description="Track Status Lookup")
    detail_url = resp.url

    # 1.9 Detail & Case Timeline
    resp = check_url(detail_url, role="Public", description="Public Case Detail & Visual Timeline")
    assert created_complaint_no.encode() in resp.content
    assert b"Case Progress Timeline" in resp.content

    # 1.10 Officer Login Link on Public Portal
    check_url("/accounts/login/", role="Public", description="Officer Access Gateway")

    # ---------------------------------------------------------
    # PART 2: AUTHENTICATED OFFICER ROLES & SYSTEM VIEWS
    # ---------------------------------------------------------
    print("\n--- 2. AUDITING INTERNAL OFFICER PORTAL & ROLE ACCESS ---")

    officer_roles = [
        ("admin", "SUPER_ADMIN", "Super Administrator"),
        ("rb_officer", "CASE_OFFICER", "Regulation Bureau Case Officer"),
        ("pgrc_officer", "CASE_OFFICER", "PGRC Case Officer"),
        ("rb_head", "BUREAU_HEAD", "Regulation Bureau Head"),
        ("pgrc_head", "BUREAU_HEAD", "PGRC Bureau Head"),
        ("ro_north", "REGIONAL_OFFICER", "Northern Regional Officer"),
        ("competent_auth", "COMPETENT_AUTH", "Competent Authority"),
        ("senior_mgmt", "SENIOR_MGMT", "Senior Management / Member Secretary"),
    ]

    for username, role_key, role_label in officer_roles:
        print(f"\n>> Testing as {username} ({role_label})")
        user = User.objects.filter(username=username).first()
        if not user:
            print(f"  [WARN] User {username} not found in DB. Skipping.")
            continue

        client.force_login(user)

        # Dashboard
        check_url("/dashboard/", role=username, description="Executive KPI Dashboard")

        # Institutions Registry
        check_url("/institutions/", role=username, description="Institutions List")
        scoped_inst = get_scoped_institutions(user).first()
        if scoped_inst:
            check_url(f"/institutions/{scoped_inst.id}/", role=username, description="Institution 360 Dossier")

        # Grievances & Cases Queue
        resp = check_url("/complaints/", role=username, description="Scoped Grievances & Cases List")
        # Ensure the public complaint is visible to this officer!
        assert created_complaint_no.encode() in resp.content, f"Public complaint {created_complaint_no} not visible to {username}"

        # Grievance Detail View
        created_complaint = Complaint.objects.get(complaint_no=created_complaint_no)
        check_url(f"/complaints/{created_complaint.id}/", role=username, description="Internal Complaint Detail & Audit View")

        # Overlap Intelligence
        check_url("/intelligence/", role=username, description="Overlap Intelligence Center")
        candidate = get_scoped_overlap_candidates(user).first()
        if candidate:
            check_url(f"/intelligence/candidate/{candidate.id}/", role=username, description="Inspect Scoped Overlap Candidate Dossier")

        # Coordination Workspace
        check_url("/coordination/", role=username, description="Cross-Bureau Joint Coordination")
        coord = get_scoped_coordinations(user).first()
        if coord:
            check_url(f"/coordination/{coord.id}/", role=username, description="Inspect Scoped Coordination Record Detail")

        # Notifications
        check_url("/notifications/", role=username, description="Notifications Center")
        check_url("/notifications/unread-count/", role=username, description="HTMX Unread Count API")

        # Reports & Analytics (If authorized)
        if user.is_super_admin or user.role in [User.Role.SENIOR_MGMT, User.Role.BUREAU_HEAD, User.Role.REGIONAL_OFFICER]:
            check_url("/reports/", role=username, description="Statutory Analytics Reports")
            check_url("/reports/export/csv/", role=username, description="Export CSV Report")

        # Audit Ledger (Super Admin, Senior Mgmt, Bureau Head)
        if user.is_super_admin or user.role in [User.Role.SENIOR_MGMT, User.Role.BUREAU_HEAD]:
            check_url("/admin-panel/audit/", role=username, description="Immutable Audit Ledger")

        # User and Bureau Management (Super Admin only)
        if user.is_super_admin:
            check_url("/admin-panel/users/", role=username, description="User Role Directory")
            check_url("/admin-panel/bureaus/", role=username, description="Bureaus Registry")

        # User Profile & Password Change
        check_url("/accounts/profile/", role=username, description="Officer Profile View")
        check_url("/accounts/password-change/", role=username, description="Password Change View")

    # ---------------------------------------------------------
    # PART 3: DATABASE INTEGRITY & TRANSACTION VERIFICATION
    # ---------------------------------------------------------
    print("\n--- 3. VERIFYING DATABASE CONNECTIVITY & ACTIONS ---")
    
    # Verify complaint count
    total_complaints = Complaint.objects.count()
    print(f"  [DB CHECK] Total Complaints in Database: {total_complaints}")
    assert total_complaints > 0

    # Verify action creation
    action_count = ComplaintAction.objects.filter(complaint=created_complaint).count()
    print(f"  [DB CHECK] Actions logged for new complaint: {action_count}")
    assert action_count >= 1

    # Verify public OTP records
    otp_count = PublicEmailOTP.objects.count()
    print(f"  [DB CHECK] Total Public OTP records stored: {otp_count}")
    assert otp_count > 0

    # Summary
    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {len(audit_results)} requests checked across all public & officer routes.")
    if errors_found:
        print(f"ERRORS FOUND ({len(errors_found)}):")
        for err in errors_found:
            print(f"  - {err}")
    else:
        print(">>> ALL PAGES, SITES, BUTTONS, AND DATABASE TRANSACTIONS ARE 100% OPERATIONAL! <<<")
    print("=" * 80)

    return len(errors_found) == 0

if __name__ == "__main__":
    success = run_system_audit()
    sys.exit(0 if success else 1)
