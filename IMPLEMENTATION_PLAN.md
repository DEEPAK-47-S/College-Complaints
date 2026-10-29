# AUGIS – AICTE Unified Grievance Intelligence System
## Master Implementation Plan & Phase Roadmap

---

### Phase Roadmap & Execution Sequence

```mermaid
gantt
    title AUGIS Phased Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Architectural Foundation
    Phase 0: Planning & Documentation   :done, p0, 2026-10-26, 1d
    Phase 1: Project Foundation & Auth  :active, p1, after p0, 1d
    section Core Domain Entities
    Phase 2: Institutions & Bureaus     :p2, after p1, 1d
    Phase 3: Complaints & Workflow FSM  :p3, after p2, 1d
    section Intelligence & Coordination
    Phase 4: Hybrid Overlap Engine      :p4, after p3, 1d
    Phase 5: Cross-Bureau Coordination  :p5, after p4, 1d
    section Insights & Governance
    Phase 6: Dashboard & Inst 360°      :p6, after p5, 1d
    Phase 7: SLA & Notifications        :p7, after p6, 1d
    Phase 8: Reports & Exports          :p8, after p7, 1d
    section Hardening & Delivery
    Phase 9: UI/UX & Responsive Polish  :p9, after p8, 1d
    Phase 10: Security & QA (T01 - T30) :p10, after p9, 1d
    Phase 11: Deployment & Demo Seeder  :p11, after p10, 1d
```

---

### Detailed Phase Milestones & Acceptance Criteria

#### Phase 0: Research & Planning (COMPLETED)
- Deliverables: `REQUIREMENTS.md`, `ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `UI_SITEMAP.md`, `USER_ROLES.md`, `WORKFLOW_RULES.md`, `AI_MATCHING_ENGINE.md`, `SECURITY.md`, `IMPLEMENTATION_PLAN.md`, `DEVELOPMENT_PROGRESS.md`.
- Acceptance: Every requirement traced to module and verification test scenario.

#### Phase 1: Project Foundation & Custom User Model
- Modular Django configuration (`config/settings/base.py`, `development.py`, `production.py`).
- Custom `User` model inheriting from `AbstractBaseUser` with UUID primary key, `role`, `assigned_bureau`, and `authorized_region`.
- Bootstrap 5 + Custom Design System tokens (`static/css/augis.css`, `base.html`).
- Authentication views (Login, Logout, Profile, Password Change, Access Denied).
- Verification: Django system checks pass; migrations apply cleanly; login/logout works.

#### Phase 2: Institution & Bureau Management
- `Institution` model with `aicte_permanent_id` unique constraint, `normalized_name`, regional attributes.
- `Bureau` model with standard units (`RB`, `PGRC`, `RO_NORTH`, `RO_SOUTH`, `APPROVAL_BUREAU`).
- Institution registry with search, filter by region/status, and CRUD views.
- Verification: Permanent ID uniqueness enforced (T04); CRUD operations persist; object-level security verified.

#### Phase 3: Complaint Lifecycle & Workflow Engine
- `Complaint`, `ComplaintCategory`, `ComplaintDocument`, `ComplaintAction`, `ComplaintTransfer`, `ComplaintEscalation`.
- Safe atomic ID generation (`AICTE-YYYY-BUR-XXXXX`).
- State machine transition service with atomic transactions (`apps.workflows.services`).
- Private document upload & streamed download view.
- Verification: Unique complaint IDs under concurrency (T05, T06); valid/invalid transitions enforced (T07, T08, T09, T10); documents protected (T25, T26).

#### Phase 4: Hybrid Overlap Detection Engine
- Deterministic match on AICTE Permanent ID and normalized names.
- Scikit-learn TF-IDF + Sentence-Transformers semantic text similarity.
- Canonical pair ordering constraint on `OverlapCandidate`.
- Explainable scoring breakdown: Institution match (0.35) + Category match (0.25) + Semantic match (0.40).
- Overlap review workflow: Confirm related, Dismiss false positive, Separate issues.
- Verification: Same-institution detection (T11); semantic similarity detection (T12); distinct issue separation (T13); human review flow (T14, T15); AI fallback resilience (T16).

#### Phase 5: Cross-Bureau Coordination Workspace
- `CoordinationRecord` with participating bureaus, coordinating lead bureau, shared action plan, deadlines.
- Advisory conflict warning when handling complaints linked to active coordination.
- Joint action timeline and shared remarks.
- Verification: Original complaint identities preserved (T18); unauthorized cross-bureau mutation prevented (T19).

#### Phase 6: Analytical Dashboard & Institution 360°
- Role-scoped KPI metrics (Total, Pending, Under Process, Transferred, Escalated, Disposed, Overdue, Overlaps).
- Chart.js visualizations (Bureau workload, monthly trends, regional distribution).
- **Institution 360° Dossier**: Unified view showing all bureau complaints, active overlaps, regulatory history.
- Verification: Direct database aggregation equality (T22).

#### Phase 7: SLA Monitoring & Notifications
- Configurable `SLAPolicy` with working day / calendar day rules.
- Management command `check_sla_breaches` with idempotent notification dispatch.
- In-app notification center and real-time HTMX unread badge.
- Verification: Overdue alerts dispatched (T20); zero duplicate notifications on repeated execution (T21).

#### Phase 8: Reporting & Filtered Exports
- Export service generating CSV, XLSX, and formatted PDF reports.
- Authorization scoping applied to all exported datasets.
- Verification: Export data matches filtered views (T24).

#### Phase 9: UI/UX & Responsive Polish
- Responsive layout verification across 360px, 768px, 1024px, 1366px, 1920px.
- Polished empty states, accessible contrast, keyboard accessibility.
- Dark / Light theme toggle.

#### Phase 10: Security Hardening & Automated QA
- Comprehensive Django test suite verifying test cases T01 through T30.
- Production security check (`manage.py check --deploy`).
- File upload restriction tests and path traversal defense tests.

#### Phase 11: Deployment, Demo Seeder & Delivery Packaging
- Synthetic demo data generator (`seed_augis_demo`) provisioning 50 institutions and 200 realistic complaints.
- Dockerfile, `docker-compose.yml`, and production Gunicorn + WhiteNoise configuration.
- Complete documentation suite and packaging.
