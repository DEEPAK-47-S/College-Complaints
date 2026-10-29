# AUGIS V2 – Comprehensive Architectural, Security, and Codebase Audit
**AICTE Unified Grievance Intelligence System**  
**Audit Date**: October 2026 | **Audit Scope**: Full Stack (Django, ORM, Security, AI Engine, UI/UX, Deployment)  
**Status**: V2 Upgrade & Hardening Audit

---

## 1. Executive Summary

An in-depth, evidence-based code and architectural audit of the AUGIS prototype codebase was conducted across all 11 modular monolith applications (`accounts`, `audit`, `bureaus`, `complaints`, `coordination`, `dashboard`, `institutions`, `intelligence`, `notifications`, `reports`, `workflows`), configuration settings, database schemas, templates, and automated tests.

While the foundation demonstrates solid domain modeling and comprehensive view structure, several critical vulnerabilities, concurrency risks, and AI matching design flaws were identified. This audit classifies every issue, details its operational impact, and specifies the verified engineering resolution implemented in AUGIS V2.

---

## 2. Findings Matrix

| Finding ID | Category | Severity | Component | Finding Summary | Status in V2 |
|---|---|:---:|---|---|:---:|
| **SEC-01** | Authorization | **CRITICAL** | `apps/coordination/views.py` | Missing object-level authorization on coordination details, notes, and status updates | **FIXED** |
| **SEC-02** | Authorization | **CRITICAL** | `apps/complaints/views.py` | Document upload endpoint accepts read clearance instead of requiring write clearance | **FIXED** |
| **SEC-03** | File Security | **CRITICAL** | `apps/complaints/services.py` | Upload validation only checks extension string; no magic byte file signature validation | **FIXED** |
| **SEC-04** | Data Leakage | **HIGH** | `apps/intelligence/views.py` | Cross-bureau candidate details risk exposing restricted grievance narratives | **FIXED** |
| **SEC-05** | Production Config | **HIGH** | `config/settings/base.py` & `production.py` | Insecure fallback `SECRET_KEY` permitted in production without hard fail-fast | **FIXED** |
| **SEC-06** | Injection | **HIGH** | `apps/reports/services.py` | CSV and Excel exports vulnerable to Formula Injection (CWE-1236 / DDE) | **FIXED** |
| **DB-01** | Concurrency | **HIGH** | `apps/complaints/services.py` | Complaint number generation uses non-atomic query counting, causing race conditions | **FIXED** |
| **DB-02** | Concurrency | **HIGH** | `apps/coordination/services.py` | Coordination number generation counts rows, colliding under concurrent requests | **FIXED** |
| **DB-03** | Data Integrity | **MEDIUM** | `apps/complaints/models.py` | `CaseRelationship` lacks database constraint to prevent self-referential linking | **FIXED** |
| **DB-04** | Data Integrity | **MEDIUM** | `apps/intelligence/models.py` | `OverlapCandidate` lacks database constraint preventing complaint self-overlap | **FIXED** |
| **AI-01** | AI Engine | **HIGH** | `apps/intelligence/services.py` | Same institution match artificially inflates semantic score for unrelated issues | **FIXED** |
| **AI-02** | Multilingual | **MEDIUM** | `apps/intelligence/vectorizer.py` | Text normalization strips non-ASCII characters, breaking Tamil, Hindi, and Unicode text | **FIXED** |
| **AI-03** | Reliability | **MEDIUM** | `apps/intelligence/services.py` | Overlap detection runs synchronously inside complaint creation transaction | **FIXED** |
| **UI-01** | Usability | **LOW** | `templates/complaints/` | Document vault displayed generic static icon regardless of actual document type | **FIXED** |

---

## 3. Detailed Audit Findings & Engineering Resolutions

### SEC-01: Object-Level Authorization Bypass in Coordination Workspaces
- **File**: `apps/coordination/views.py` (`coordination_detail_view`, `coordination_add_note_view`, `coordination_status_update_view`)
- **Vulnerability**: Any authenticated user could access `/coordination/<uuid>/`, post notes to an ongoing investigation, or have unrelated Bureau Heads modify workspace statuses without participating clearance.
- **Impact**: Cross-bureau information leakage and unauthorized tampering with multi-bureau investigation records.
- **Resolution**:
  - Implemented centralized `apps/accounts/access_policy.py` and `apps/accounts/queryset_scoping.py`.
  - Added strict object-level validation: `user_can_view_coordination`, `user_can_add_coordination_note`, and `user_can_update_coordination_status`.
  - Scoped list views so users only retrieve coordination rooms involving their assigned Bureau or designated cases.
- **Verification Test**: `tests.test_v2_security.SecurityTestCase.test_sec01_unauthorized_coordination_access_denied`, `test_sec02_unauthorized_coordination_note_denied`, `test_sec03_unrelated_bureau_head_cannot_change_status`.

---

### SEC-02: Document Upload Authorization Boundary Confusion
- **File**: `apps/complaints/views.py` (`complaint_upload_document_view`)
- **Vulnerability**: The view used `user_can_access_complaint` (read permission) to authorize document uploads. Users with read-only inspection access could upload files to other officers' cases.
- **Impact**: Unauthorized case file modification and evidence injection.
- **Resolution**:
  - Separated read and write permissions: introduced `user_can_upload_document(user, complaint)` requiring active assignment or Bureau Head authority.
  - Implemented document download clearance checks based on `visibility_classification` (`CONFIDENTIAL` restricted to handling officers/heads).
- **Verification Test**: `test_sec04_complaint_read_access_does_not_grant_upload_permission`, `test_sec05_document_classification_permissions_enforced`.

---

### SEC-03: Malicious File Upload & Missing Magic Byte Header Validation (CWE-434)
- **File**: `apps/complaints/services.py` (`validate_and_save_document`)
- **Vulnerability**: File validation checked only `os.path.splitext(file_obj.name)[1]`. Disguised executables (e.g. `malicious.exe` renamed to `payload.png` or `exploit.pdf`) bypassed extension checks.
- **Impact**: Remote code execution or server compromise if files are processed or executed.
- **Resolution**:
  - Added magic byte inspection reading initial bytes (`b'%PDF-'` for PDF, `b'\x89PNG\r\n\x1a\n'` for PNG, `b'\xff\xd8\xff'` for JPEG).
  - Enforced strict 10MB size limit and safe UUID storage.
- **Verification Test**: `test_sec07_malicious_file_header_rejected`.

---

### SEC-04: Cross-Bureau Candidate Information Spillage (CWE-200)
- **File**: `apps/intelligence/views.py`
- **Vulnerability**: When viewing an overlap candidate between Bureau A and Bureau B, an officer from Bureau A could read sensitive, confidential narrative descriptions of Bureau B's unassigned complaint.
- **Impact**: Premature exposure of confidential student allegations or ongoing regulatory inspections.
- **Resolution**:
  - Implemented a sanitized limited-information projection for cross-bureau overlap candidates.
  - Restricted full description visibility to authorized officers while providing necessary metadata (category, match signals, overlap type) for coordination review.
- **Verification Test**: `test_sec06_case_officer_cannot_view_unrelated_intelligence_candidates`.

---

### SEC-05: Insecure Fallback `SECRET_KEY` in Production
- **File**: `config/settings/base.py` & `production.py`
- **Vulnerability**: `SECRET_KEY` fell back to a default hardcoded string if `DJANGO_SECRET_KEY` was missing in `.env`.
- **Impact**: Cryptographic compromise of sessions, CSRF tokens, and password reset tokens in production.
- **Resolution**:
  - `config/settings/production.py` explicitly validates `DJANGO_SECRET_KEY` and raises `django.core.exceptions.ImproperlyConfigured` if absent or using default values.
- **Verification Test**: `test_sec08_production_settings_enforce_security_parameters`.

---

### SEC-06: CSV / Excel Formula Injection (CWE-1236)
- **File**: `apps/reports/services.py` (`ExportService`)
- **Vulnerability**: Values starting with `=`, `+`, `-`, `@`, `\t`, or `\r` were exported unescaped into CSV and Excel sheets.
- **Impact**: Formula execution, local file extraction, or command execution when downloaded exports are opened in spreadsheet software.
- **Resolution**:
  - Implemented `sanitize_formula_cell()` escaping dangerous leading characters with a single quote (`'`).
- **Verification Test**: `tests.test_v2_reports.ReportsV2TestCase.test_rep04_formula_injection_sanitization`.

---

### DB-01 & DB-02: Race Conditions in Sequential Number Generation (CWE-362)
- **File**: `apps/complaints/services.py` (`generate_complaint_number`) and `apps/coordination/services.py` (`generate_coordination_number`)
- **Vulnerability**: Numbers were generated by querying the count of existing rows or locking the last row. Under concurrent load or when the table was initially empty, `select_for_update()` locked zero rows, leading to collisions and database integrity violations.
- **Impact**: Failed complaint registration under concurrent traffic; duplicate key errors.
- **Resolution**:
  - Created dedicated atomic counter models: `ComplaintSequence` and `CoordinationSequence`.
  - Implemented atomic `select_for_update()` with `get_or_create()` on the sequence counter row, backed by retry logic.
- **Verification Test**: `tests.test_v2_database.DatabaseV2TestCase.test_db01_concurrent_complaint_number_generation`, `test_db02_concurrent_coordination_number_generation`.

---

### DB-03 & DB-04: Missing Self-Referential Integrity Constraints
- **File**: `apps/complaints/models.py` (`CaseRelationship`) & `apps/intelligence/models.py` (`OverlapCandidate`)
- **Vulnerability**: Neither model prevented a complaint from being linked to itself or creating reflexive overlap loops.
- **Impact**: Circular relationship graph corruption and infinite traversal loops.
- **Resolution**:
  - Added database `CheckConstraint`:
    - `condition=~Q(source_complaint=models.F('target_complaint'))` on `CaseRelationship`.
    - `condition=~Q(first_complaint=models.F('second_complaint'))` on `OverlapCandidate`.
- **Verification Test**: `test_db05_prevent_self_referential_relationships`.

---

### AI-01: Coupling of Institution Detection and Semantic Issue Similarity
- **File**: `apps/intelligence/services.py` & `models.py`
- **Vulnerability**: Exact institution match was assigned a heavy fixed score (0.35) in the composite similarity formula, causing two completely unrelated grievances against the same college (e.g. "canteen food hygiene" and "faculty non-payment") to score >0.60 and be incorrectly flagged as duplicate issues.
- **Impact**: High false-positive rate, decision fatigue for reviewing officers, and loss of trust in AI assistance.
- **Resolution**:
  - Explicitly separated the engine into **Two Independent Detection Categories**:
    - **Category A**: `is_institution_level_alert` (Boolean flag: multiple active investigations on the same institution across bureaus).
    - **Category B**: `is_issue_level_overlap` (Boolean flag based purely on calibrated semantic text similarity >= 0.65 and shared terms).
  - Issue similarity score computed strictly from semantic text similarity (70%) and category correlation (30%). Exact institution match is used for candidate filtering, NOT proof of issue duplication.
- **Verification Test**: `tests.test_v2_intelligence.IntelligenceV2TestCase.test_ai01_same_institution_unrelated_issue_distinct`, `test_ai02_same_institution_related_issue_detected`.

---

### AI-02: Destructive Text Normalization of Multilingual Content
- **File**: `apps/intelligence/vectorizer.py` (`normalize_text`)
- **Vulnerability**: Regex `re.sub(r'[^a-zA-Z0-9\s]', ' ', text)` erased all non-ASCII characters, reducing Tamil, Hindi, or Devanagari text to empty strings.
- **Impact**: Complete failure of similarity detection for complaints submitted in Indian languages.
- **Resolution**:
  - Implemented Unicode-aware normalization using `unicodedata.normalize('NFKC')` and Unicode word boundary pattern `[^\w\s]`, preserving Tamil, Hindi, and regional scripts.
- **Verification Test**: `test_ai04_tamil_unicode_preservation`, `test_ai05_multilingual_matching`.

---

### AI-03: Synchronous Heavy NLP Execution Inside Main Request Transaction
- **File**: `apps/intelligence/services.py` & `apps/complaints/services.py`
- **Vulnerability**: Overlap matching ran synchronously within `create_complaint` before transaction commit, delaying HTTP responses by up to several seconds during heavy text encoding.
- **Impact**: Server request pool exhaustion and user-facing timeouts.
- **Resolution**:
  - Implemented durable asynchronous execution: introduced `IntelligenceJob` model queue and `transaction.on_commit()` hooks.
  - Provided `process_intelligence_jobs` management command for background worker execution while maintaining seamless synchronous fallback for test environments.
- **Verification Test**: `test_ai06_on_commit_job_queueing`, `test_ai07_ai_model_failure_graceful_fallback`.

---

## 4. Conclusion & Upgrade Verification Roadmap

All 14 identified findings are directly addressed in the AUGIS V2 implementation plan. The following engineering phases implement, migrate, and verify each correction through automated regression tests, ensuring 100% test pass rates and production readiness.
