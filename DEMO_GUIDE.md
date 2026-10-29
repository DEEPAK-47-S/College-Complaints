# AUGIS – AICTE Unified Grievance Intelligence System
## Demonstration & Evaluation Walkthrough Guide

**Product Identity**: AUGIS (One Institution. One Unified View. Coordinated Action)  
**Notice**: Proposed academic/prototype solution for AICTE grievance monitoring and cross-bureau intelligence.

---

### 1. Pre-Configured Demonstration Accounts

All demonstration accounts are provisioned with the standard password: **`Augis@2026`**

| Role | Username | Password | Purpose & Scope |
|---|---|---|---|
| **Super Administrator** | `admin` | `Augis@2026` | Full administrative access, global dashboard, user directory, audit ledger. |
| **Bureau Head (RB)** | `rb_head` | `Augis@2026` | Regulation Bureau head: officer assignment, transfer approvals, overlap review. |
| **Bureau Head (PGRC)** | `pgrc_head` | `Augis@2026` | Public Grievance Redressal Cell head: grievance oversight and joint coordination. |
| **Case Officer (RB)** | `rb_officer` | `Augis@2026` | Day-to-day scrutiny of RB cases, document uploads, action remarks. |
| **Case Officer (PGRC)** | `pgrc_officer`| `Augis@2026` | Day-to-day handling of student/public grievances. |
| **Regional Officer** | `ro_north` | `Augis@2026` | Northern region jurisdictional oversight and field inspection reports. |
| **Senior Management** | `senior_mgmt` | `Augis@2026` | Consolidated multi-bureau executive analytics and export generation. |
| **Competent Authority** | `competent_auth`| `Augis@2026`| Final statutory decision-maker for escalated disputes and consensus orders. |

---

### 2. Primary Showcase Scenario: Cross-Bureau Synergy

#### Background Context
An educational institution (e.g. *Apex Institute of Higher Learning*) faces an inspection finding in the **Regulation Bureau (RB)** regarding laboratory norm non-compliance. Concurrently, a student petition arrives at the **Public Grievance Redressal Cell (PGRC)** regarding broken computing facilities.

In conventional uncoordinated systems, these cases proceed independently, risking duplicate inspections and conflicting findings.

Here is how AUGIS eliminates this fragmentation:

---

#### Step 1: Unified Command Dashboard
1. Open browser at `http://127.0.0.1:8000/accounts/login/`.
2. Sign in as `admin` (Password: `Augis@2026`).
3. Land on `/dashboard/`:
   - Inspect the **Live KPI Cards**: Total Cases (200), Pending, Under Process, Overdue SLA breaches.
   - Inspect the **Chart.js Visualizations**: 6-Month Intake vs. Disposal Velocity and Bureau Workload Distribution.
   - Observe the **Urgent Action Alerts** on the right sidebar.

---

#### Step 2: Unique Feature – Institution 360° Dossier
1. Navigate to **Institutions Registry** (`/institutions/`).
2. Search for `Apex` or click **"360° Dossier"** on the first institution.
3. Land on `/institutions/<uuid>/360/`:
   - Observe the **Mandatory Dual-Layer Overlap Banner**:
     - **Layer A (Institution-Level)**: Alerts that multiple AICTE units (e.g. RB and PGRC) are concurrently scrutinizing this institution.
     - **Layer B (Issue-Level)**: Highlights whether separate cases share identical underlying disputes.
   - Review the complete chronological grievance history across all bureaus.

---

#### Step 3: Primary Innovation – Overlap Intelligence Center
1. In the sidebar, click **Overlap Intelligence** (`/intelligence/`).
2. Observe the candidate pairs detected by the hybrid deterministic + semantic NLP engine.
3. Filter by **"Cross-Bureau Only"** to isolate cases handled independently across departments.
4. Click **"Inspect"** on any candidate pair:
   - Review the **Combined Overlap Index** (e.g. 84%).
   - Inspect the **Explainable AI Evidence Breakdown**:
     - Exact AICTE Permanent ID Match.
     - Cross-Bureau Alert: Handled by RB vs PGRC.
     - NLP Cosine Similarity score.
     - Shared salient keywords (e.g. *laboratory, equipment, facilities*).
   - Review the side-by-side grievance narratives.

---

#### Step 4: Human Review & Decision Support
*(AI never closes or disposes cases automatically)*
1. In the inspection view, enter review remarks: *"Confirmed cross-bureau overlap on laboratory equipment standards."*
2. Click **"Confirm Related Issue"**.
3. A confirmed `CaseRelationship` is recorded in the immutable audit ledger.
4. Click **"Establish Joint Coordination Workspace"**.

---

#### Step 5: Cross-Bureau Coordination Workspace
1. In the Coordination room (`/coordination/<uuid>/`):
   - Notice the designated **Lead Coordinating Bureau** (RB) and **Member Bureau** (PGRC).
   - Verify that **both original complaint IDs and histories remain completely intact** (no destructive merging).
   - Post a joint remark: *"RB inspector and PGRC nodal officer will conduct a single consolidated campus visit on Friday."*
   - Observe the remark recorded on the shared inter-bureau timeline.

---

#### Step 6: Case Officer Workflow & Private Vault
1. Log out and sign in as `rb_officer` (Password: `Augis@2026`).
2. Open the assigned complaint:
   - Add an action remark: *"Notice served to institution for explanation."*
   - Click **"Attach File"** and upload a PDF inspection note.
   - Verify the file is stored with a secure SHA-256 checksum in the private vault.
   - Note: Officers from other bureaus cannot download restricted documents without explicit authorization (enforced with HTTP 403).

---

#### Step 7: Reports & Filtered Exports
1. Navigate to **Analytics & Exports** (`/reports/`).
2. Filter complaints by status or handling bureau.
3. Click **"Export CSV"**, **"Export Excel"**, or **"Export PDF"**.
4. Confirm downloads generate cleanly formatted tables respecting role permissions.

---

#### Step 8: Immutable Audit Trail
1. Sign in as `admin`.
2. In the sidebar, click **Audit Ledger** (`/admin-panel/audit/`).
3. Verify that every login, status change, document upload, and overlap review is permanently recorded with actor identity, timestamp, and request correlation ID.
