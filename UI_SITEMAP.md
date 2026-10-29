# AUGIS – AICTE Unified Grievance Intelligence System
## UI Sitemap, Wireframe Flow & Navigation Hierarchy

---

### 1. Complete Application Navigation Hierarchy

```text
AUGIS Web Application
│
├── Authentication & Identity
│   ├── /accounts/login/                 [Login with secure CSRF, lockout guard]
│   ├── /accounts/logout/                [Safe POST logout]
│   ├── /accounts/profile/               [User profile, bureau, active role badges]
│   ├── /accounts/password-change/       [Standard credential renewal]
│   └── /access-denied/                  [403 Friendly diagnostic page with contact info]
│
├── Central Command Dashboard
│   └── /dashboard/                      [Main intelligence dashboard with live DB KPIs]
│
├── Institution Registry & 360° Dossier
│   ├── /institutions/                   [Paginated registry with quick search & filters]
│   ├── /institutions/new/               [Create new verified institution]
│   ├── /institutions/<id>/              [Standard details, operational status]
│   ├── /institutions/<id>/edit/         [Update address, contact info]
│   └── /institutions/<id>/360/          [★ UNIQUE: Institution 360° consolidated dossier]
│
├── Complaint Lifecycle Management
│   ├── /complaints/                     [Advanced filterable case grid: bureau, SLA, status]
│   ├── /complaints/new/                 [New complaint intake with auto ID generator]
│   ├── /complaints/<id>/                [Tabbed complaint details view]
│   │   ├── Tab 1: Overview              [Core metadata, complainant ref, institution card]
│   │   ├── Tab 2: Action Timeline       [Chronological audit trail of all movements]
│   │   ├── Tab 3: Documents             [Restricted private file repository]
│   │   ├── Tab 4: Overlaps & Relations  [Detected matches, category similarity badges]
│   │   ├── Tab 5: Coordination Records  [Active joint bureau plans]
│   │   └── Tab 6: Audit Events          [Raw security & mutation ledger]
│   ├── /complaints/<id>/assign/         [Assign/reassign officer modal/endpoint]
│   ├── /complaints/<id>/transition/     [Status update engine: Pending -> Under Process, etc.]
│   ├── /complaints/<id>/transfer/       [Inter-bureau transfer request & approval]
│   ├── /complaints/<id>/escalate/       [Competent authority escalation]
│   └── /complaints/<id>/documents/upload/ [Private document ingestion with validation]
│
├── Intelligence & Overlap Center
│   ├── /intelligence/                   [★ PRIMARY INNOVATION: Overlap detection dashboard]
│   ├── /intelligence/candidate/<id>/    [Explainable overlap inspector with vector metrics]
│   └── /intelligence/candidate/<id>/review/ [Human review: Confirm, Dismiss, or Separate]
│
├── Cross-Bureau Coordination Workspace
│   ├── /coordination/                   [★ UNIQUE: Active joint inter-bureau cases]
│   ├── /coordination/new/               [Initiate coordination from reviewed overlap]
│   ├── /coordination/<id>/              [Coordination room: participating bureaus, plan]
│   └── /coordination/<id>/action/       [Log shared remarks, update next milestones]
│
├── Notifications & SLA Monitoring
│   ├── /notifications/                  [Notification center, unread filter, mark read]
│   └── /notifications/unread-count/     [HTMX polling endpoint for top-bar badge]
│
├── Analytical Reports & Data Exports
│   ├── /reports/                        [Analytics overview & metric charts]
│   ├── /reports/institutions/export/    [CSV / Excel / PDF institution complaints]
│   ├── /reports/bureaus/export/         [Bureau workload & disposal efficiency]
│   └── /reports/sla-breaches/export/    [Overdue analysis & compliance audit]
│
└── Governance & Administration
    ├── /admin-panel/users/              [RBAC User directory, roles, bureau assignment]
    ├── /admin-panel/bureaus/            [AICTE Bureau configuration]
    ├── /admin-panel/categories/         [Configurable complaint categories & SLAs]
    ├── /admin-panel/sla-policies/       [SLA duration, working day calendar rules]
    └── /admin-panel/audit/              [System-wide immutable audit inspector]
```

---

### 2. Design Tokens & Visual Hierarchy

- **Color Palette**:
  - Primary Brand: `#12345A` (AICTE Deep Navy)
  - Secondary Accent: `#2563EB` (Action Cobalt)
  - Background Tint: `#F5F7FB` (Accessible Soft Light)
  - Card Surface: `#FFFFFF` (Clean White)
  - Success Indicator: `#15803D` (Forest Green - Disposed / Compliant)
  - Warning Indicator: `#B45309` (Amber - Approaching SLA / Review Needed)
  - Danger Indicator: `#B91C1C` (Crimson - Overdue / Escalated / High Risk)
  - Dark Neutral: `#172033` (High Contrast Text)
- **Typography**:
  - Display & Headings: `Outfit`, sans-serif (clean, authoritative modern geometry)
  - Body & Form Controls: `Inter`, -apple-system, BlinkMacSystemFont, sans-serif
- **Micro-Interactions**:
  - Smooth 150ms transitions on hover states.
  - Subdued card elevation (`box-shadow: 0 1px 3px rgba(18,52,90,0.08), 0 4px 12px rgba(18,52,90,0.04)`).
  - Clear pill badges for status (`badge-pending`, `badge-under-process`, `badge-disposed`).
