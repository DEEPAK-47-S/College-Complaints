# AUGIS – AICTE Unified Grievance Intelligence System
## Role-Based Access Control (RBAC) & Object-Level Permission Matrix

---

### 1. Role Definitions & Scoping Boundaries

Access control in AUGIS enforces a **two-dimensional boundary**:
1. **Functional Role Permissions** (What actions the user is authorized to perform).
2. **Organizational Data Scope** (Which bureau, regional office, or assigned case records the user is authorized to read/modify).

| Role Code | Role Name | Primary Responsibilities | Data Scoping Boundary |
|---|---|---|---|
| `SUPER_ADMIN` | **Super Administrator** | System administration, user provisioning, bureau configuration, SLA policies, security audit review. | Global system-wide visibility. Cannot modify judicial/statutory remarks of officers. |
| `BUREAU_HEAD` | **Bureau Head** | Oversees bureau operations (e.g., RB or PGRC), assigns officers, approves transfers, reviews overlap alerts, initiates coordination. | Full read/write for own Bureau. Authorized read-only for cross-bureau overlap candidates involving their Bureau. |
| `CASE_OFFICER` | **Case Officer** | Day-to-day handling of assigned complaints, upload scrutiny documents, add action remarks, request transfer/escalation. | Write access restricted strictly to assigned cases. Read access to own Bureau cases. Cannot edit other bureaus' files. |
| `REGIONAL_OFFICER` | **Regional Officer** | Regional oversight, inspection reports, field scrutiny remarks within designated AICTE geographic region. | Filtered strictly by `user.authorized_region == institution.region`. |
| `SENIOR_MGMT` | **Senior Management** | High-level analytical dashboards, cross-bureau performance, bottleneck monitoring, SLA compliance audits. | Read-only across all Bureaus and Regions. Export reports. No direct case modification. |
| `COMPETENT_AUTH` | **Competent Authority** | Executive statutory decisions on escalated cases, high-stakes institutional scrutiny, approval of final disposals. | Full access to escalated cases across bureaus. Authorized to record binding decision remarks. |

---

### 2. Functional Permission Matrix

| Capability / Action | SUPER_ADMIN | BUREAU_HEAD | CASE_OFFICER | REGIONAL_OFFICER | SENIOR_MGMT | COMPETENT_AUTH |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Manage Users & Bureaus** | Yes | No | No | No | No | No |
| **Configure SLA Policies** | Yes | No | No | No | No | No |
| **View Audit Ledger** | Yes | Own Bureau | No | No | Yes | Yes |
| **Register New Complaint** | Yes | Yes | Yes | Yes | No | No |
| **Assign / Reassign Officer** | Yes | Own Bureau | No | No | No | No |
| **Update Complaint Status** | Admin override | Yes (Bureau) | Yes (Assigned) | Region assigned | No | Escalated cases |
| **Upload Private Documents**| Yes | Yes | Yes (Assigned) | Yes (Region) | No | Yes |
| **Download Restricted Files**| Yes | Own Bureau | Assigned/Bureau | Own Region | Yes (View) | Yes |
| **Request Case Transfer** | Yes | Yes | Yes (Assigned) | Yes | No | No |
| **Approve Case Transfer** | Yes | Yes (Target) | No | No | No | Yes |
| **Escalate Complaint** | Yes | Yes | Yes | Yes | No | No |
| **Record Escalation Decision**| No | No | No | No | No | Yes |
| **Review Overlap Alerts** | Yes | Yes (Involved) | Read only | Read only | Read only | Yes |
| **Initiate Joint Coordination**| Yes | Yes (Involved) | No | No | No | Yes |
| **Export Analytical Reports**| Yes | Yes (Bureau) | No | Region only | Yes (All) | Yes |

---

### 3. Server-Side Enforcement Architecture

- **No Security-Through-Obscurity**: Hiding UI buttons in HTML is purely ergonomic. All POST endpoints and detail views strictly execute Python decorators / permission checks:
  ```python
  def user_can_access_complaint(user, complaint):
      if user.role in ['SUPER_ADMIN', 'SENIOR_MGMT', 'COMPETENT_AUTH']:
          return True
      if user.role == 'BUREAU_HEAD' and complaint.currently_assigned_bureau == user.assigned_bureau:
          return True
      if user.role == 'CASE_OFFICER' and complaint.currently_assigned_officer == user:
          return True
      if user.role == 'REGIONAL_OFFICER' and complaint.institution.region == user.authorized_region:
          return True
      return False
  ```
- **Private Document Streaming**: Documents are streamed via Django `FileResponse` after checking `user_can_access_complaint(request.user, document.complaint)`. Direct static link traversal is blocked.
