# AUGIS – AICTE Unified Grievance Intelligence System
## System Requirements & Traceability Matrix (RTM)

**Tagline**: *One Institution. One Unified View. Coordinated Action.*  
**Notice**: Proposed academic/prototype solution for grievance monitoring, cross-bureau coordination, and intelligence support.

---

### 1. Problem Statement Analysis

In the current operational context of AICTE:
- Grievances and complaints arrive via multiple entry channels into separate units:
  - **Regulation Bureau (RB)** (Statutory compliance, unapproved courses, norm violations)
  - **Public Grievance Redressal Cell (PGRC)** (Student/faculty grievances, capitation fees, harassment)
  - **Regional Offices (RO)** (Field scrutiny, geographical jurisdiction issues)
  - **Special Cells / Committees**
- Without a consolidated, institution-centric intelligence system, multiple independent complaints against the *same institution* or regarding the *same underlying issue* can be processed in departmental silos.
- Risks identified:
  1. Duplicate investigations wasting institutional resources.
  2. Conflicting orders or contradictory factual findings.
  3. Lack of unified institutional history (an institution might appear compliant in one bureau while facing severe non-compliance complaints in another).
  4. SLA violations and delayed disposal.
  5. Inability to identify systemic or chronic non-compliance across bureaus.

---

### 2. System Boundaries & Operating Principles

1. **Decision-Support vs. Statutory Authority**:
   - AUGIS is strictly an **intelligent decision-support, monitoring, and cross-bureau coordination platform**.
   - The AI/NLP matching subsystem **never** independently makes statutory, regulatory, punitive, or disposal decisions.
   - All workflow transitions, disposals, transfers, and coordination actions require human officer confirmation.
2. **Data Integrity & Non-Destructive Operation**:
   - The system **never** merges, overwrites, or deletes original complaints when an overlap is detected.
   - Original complaint IDs, dates, audit logs, and file uploads remain immutable.
3. **Multi-Bureau Scoping & Access Control**:
   - Information access is governed strictly by Bureau code, Role type, and Geographic Region.

---

### 3. Requirements Traceability Matrix (RTM)

| Req ID | Requirement Description | Category | Implementation Module | Verification / Test Case |
|---|---|---|---|---|
| **REQ-01** | Centralized Institution Profiles with AICTE Permanent ID | Core Entity | `apps.institutions` | `T04`: Permanent ID uniqueness & CRUD |
| **REQ-02** | Multi-Bureau Complaint Ingestion & Safe Unique ID Gen | Complaint Lifecycle | `apps.complaints` | `T05`, `T06`: Unique sequential alphanumeric ID |
| **REQ-03** | Configurable Complaint Categories & Document Uploads | Ingestion | `apps.complaints` | `T25`, `T26`: Upload validation & restricted download |
| **REQ-04** | Role-Based Access Control (RBAC) with 6 Specific Roles | Security & Auth | `apps.accounts` | `T01`, `T02`, `T03`: Login, auth, and object scoping |
| **REQ-05** | State Machine Workflow (Pending, Under Process, Transferred, Escalated, Disposed) | Workflow | `apps.workflows` | `T08`, `T09`, `T10`: Permitted transitions & audit trail |
| **REQ-06** | Hybrid Overlap Engine (Institution Match + Semantic Similarity) | Intelligence | `apps.intelligence` | `T11`, `T12`, `T13`: Cross-bureau institution & semantic overlap |
| **REQ-07** | Explainable AI Similarity Scoring & Evidence Presentation | Intelligence | `apps.intelligence` | `T14`, `T15`, `T16`: Reason breakdown & NLP fallback |
| **REQ-08** | Institution 360° Consolidated Intelligence Dossier | Analytics & Visibility | `apps.institutions` / `apps.dashboard` | Complete institutional history & multi-bureau active view |
| **REQ-09** | Cross-Bureau Coordination Workspace & Advisory Conflict Alerts | Coordination | `apps.coordination` | `T18`, `T19`: Joint action planning & boundary defense |
| **REQ-10** | Configurable SLA Policies, Calendar Working Days & Alerts | SLA / Monitoring | `apps.notifications` | `T20`, `T21`: Overdue tracking & idempotent scheduler |
| **REQ-11** | Immutable Audit Trail for Actions, Status Changes & Access | Audit / Governance | `apps.audit` | Non-modifiable append-only activity log |
| **REQ-12** | Real-Time Role-Scoped Analytics & Dashboard Metrics | Reporting | `apps.dashboard` | `T22`: Zero-denominator safe database queries |
| **REQ-13** | Multi-Format Filtered Exports (PDF, CSV, Excel) | Reporting | `apps.reports` | `T24`: Authorized report generation |
| **REQ-14** | Responsive Enterprise UI (360px to 1920px) with Zero Framework Overhead | UI/UX | `templates/`, `static/` | `T27`, `T28`, `T29`: Responsive Bootstrap 5 + Vanilla CSS/JS |

---

### 4. Mandatory vs. Extended Feature Scope

#### Mandatory Features (Delivered in Core Phases)
- Custom User Model with Bureau, Region, and 6 RBAC Roles.
- Institution Registry with AICTE Permanent ID indexing, normalized names, and regional attributes.
- Full Complaint Lifecycle with Safe ID Generator (`AICTE-YYYY-BUR-XXXXX`).
- State Machine with strict transition validation, remarks, and atomic transactions.
- Document Scrutiny with checksums, private views (no public media URL exposure).
- Hybrid Overlap Detection Engine:
  - Deterministic Institution matching.
  - TF-IDF / Scikit-Learn Cosine Similarity & Sentence Transformers embedding layer.
  - Explainable factors: Institution Match Type, Category Relevance, Semantic Distance, Multi-Bureau Flag.
- Overlap Review Workflow (Confirm Related, Mark Distinct, False Positive Dismissal).
- Cross-Bureau Coordination Hub (Lead Bureau, Participating Bureaus, Shared Action Plan, Conflict Warning).
- Institution 360° View: Complete single-pane-of-glass dossier.
- SLA Management Command (`python manage.py check_sla_breaches`) with idempotent alert dispatch.
- Audit Logging on all sensitive mutations.
- Multi-format Export Service (CSV, XLSX, PDF).

#### Extended Features
- In-app Notification Drawer with HTMX real-time badge updates.
- Quick Search Keyboard Shortcuts (`/` search jump, `Esc` dismiss).
- Dark/Light Theme toggle using CSS custom properties.
- Synthetic Database Seed Command generating 50 institutions and 200 diverse cross-bureau complaints.
