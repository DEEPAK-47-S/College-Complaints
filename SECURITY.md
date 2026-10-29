# AUGIS – AICTE Unified Grievance Intelligence System
## Application Security & Data Protection Architecture

---

### 1. Threat Model & Security Controls

| Threat / Vulnerability | Risk Level | Mitigating Control in AUGIS |
|---|:---:|---|
| **Unauthorized Complaint Access** | High | Two-tier authorization: functional role check + centralized object-level access policy (`apps.accounts.access_policy`) and queryset scoping (`queryset_scoping.py`). |
| **Disguised File Upload (Magic Bytes)** | Critical | Magic byte file header inspection (`%PDF-`, `\x89PNG\r\n\x1a\n`, `\xff\xd8\xff`) verifying genuine MIME signature regardless of spoofed extensions. |
| **Document Classification Leakage** | High | Multi-level classification (`PUBLIC_RECORD`, `INTERNAL_ONLY`, `CONFIDENTIAL`). Confidential files require explicit clearance or case officer assignment. |
| **CSV / Excel Formula Injection (CWE-1236)** | High | `sanitize_formula_cell` automatically prefixes cells starting with `=`, `+`, `-`, `@`, `\t`, `\r` with a single quote (`'`). |
| **Cross-Bureau Coordination Tampering** | High | Gated coordination room access: only participating bureaus can post notes; only Lead Bureau Head / Super Admin can change status. |
| **Cross-Site Request Forgery (CSRF)** | High | Django CSRF middleware enabled on all forms; HTMX requests send `X-CSRFToken` headers. |
| **SQL Injection (SQLi)** | Critical | 100% Django ORM parameterized queries. Raw SQL strings are strictly prohibited. |
| **Cross-Site Scripting (XSS)** | High | Django template engine auto-escaping active. JSON data safely encoded with `json_script`. |
| **Direct Media File Traversal** | High | Uploaded documents stored in private storage root outside public static assets; streamed via gated streaming view. |
| **Audit Trail Tampering** | Critical | Append-only database model; normal application views have zero write/update/delete endpoints for `AuditEvent`. |

---

### 2. Centralized Access Policy & Scoping Layer

AUGIS V2 centralizes all authorization rules into `apps.accounts.access_policy` and `apps.accounts.queryset_scoping`:

- `user_can_view_complaint(user, complaint)`: Controls case visibility.
- `user_can_modify_complaint(user, complaint)`: Controls case actions and state transitions.
- `user_can_upload_document(user, complaint)`: Strictly decoupled from read access (read-only users cannot upload).
- `user_can_download_document(user, document)`: Enforces clearance for `CONFIDENTIAL` scrutiny memos.
- `user_can_view_coordination(user, coordination)`: Restricts room access to participating bureaus.
- `user_can_add_coordination_note(user, coordination)`: Blocks external officers from injecting notes.
- `user_can_update_coordination_status(user, coordination)`: Restricts coordination closure to Coordinating Bureau Lead or Super Admin.

---

### 3. Magic Byte Signature Validation & Private Document Storage

```python
# Magic byte validation in apps.complaints.services
MAGIC_SIGNATURES = {
    '.pdf': [b'%PDF-'],
    '.png': [b'\x89PNG\r\n\x1a\n'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
}
```

Files uploaded are checked against both extension whitelist and true magic byte headers. Files are written to `media_private/complaint_docs/` with UUID-based names, preventing path traversal attacks and direct file execution.

---

### 4. Formula Injection Sanitization (CWE-1236)

All tabular export routines (`ExportService.to_csv`, `ExportService.to_excel`) pipe text fields through `sanitize_formula_cell`:

```python
def sanitize_formula_cell(val):
    if val is None:
        return ''
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s
```

---

### 5. Production Environment & Secrets Policy

1. **Environment Variables**: Managed via `.env` with a strict `.env.example` template. `SECRET_KEY`, `DATABASE_URL`, and debug toggles are never committed.
2. **Security Headers**:
   - `SECURE_BROWSER_XSS_FILTER = True`
   - `SECURE_CONTENT_TYPE_NOSNIFF = True`
   - `X_FRAME_OPTIONS = 'DENY'`
   - `CSRF_COOKIE_HTTPONLY = True`
   - `SESSION_COOKIE_HTTPONLY = True`
3. **Synthetic Demonstration Data**: All seed fixtures utilize fictional institution names, synthetic complaint texts, and non-real identities. No real complainant Aadhaar, phone numbers, or confidential AICTE records are ever ingested.
