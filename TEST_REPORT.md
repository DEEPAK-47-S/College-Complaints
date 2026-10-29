# AUGIS – AICTE Unified Grievance Intelligence System
## Formal Automated Test Execution Report (V2 Hardening Suite)

**Date of Execution**: 2026-10-27  
**Test Suite**: `python manage.py test tests`  
**Execution Environment**: Python 3.12.10, Django 6.1.2, SQLite (Local Test Runner) / PostgreSQL (Production)  
**Result Summary**: **57 Tests Executed — 57 Passed — 0 Failed — 0 Errors (100% Pass Rate)**

---

### V2 Hardening & Security Test Matrix

| Test Suite & ID | Test Method & Description | Module | Result | Status |
|---|---|---|:---:|:---:|
| **SEC-01** | `test_sec01_unauthorized_coordination_detail_access_denied`: Officers outside participating bureaus receive HTTP 403 Forbidden on coordination detail. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-02** | `test_sec02_unauthorized_coordination_note_submission_denied`: Non-participating officers cannot inject notes into shared coordination rooms. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-03** | `test_sec03_unrelated_bureau_head_cannot_change_coordination_status`: Only Lead Bureau Head, Competent Authority, or Super Admin can modify coordination status. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-04** | `test_sec04_complaint_read_access_does_not_grant_upload_permission`: Read-only regional access to a complaint does not authorize uploading documents (HTTP 403). | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-05** | `test_sec05_document_classification_permissions_enforced`: Classified CONFIDENTIAL documents are restricted from unauthorized officers without explicit clearance. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-06** | `test_sec06_magic_byte_disguised_file_rejected`: File with `.png` extension but non-image header content is rejected via magic byte signature check. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-07** | `test_sec07_scoped_complaint_list_isolation`: Case officers only see complaints belonging to their assigned Bureau or region. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **SEC-08** | `test_sec08_cross_bureau_candidate_detail_projection_redacted`: Officers viewing cross-bureau overlap candidates receive redacted complaint text projections if lacking access. | `tests.test_v2_security` | **PASSED** | ✅ PASS |
| **DB-01** | `test_db01_concurrent_complaint_number_generation`: 10 simultaneous threads generate 10 unique, collision-free complaint IDs via atomic counter table. | `tests.test_v2_database` | **PASSED** | ✅ PASS |
| **DB-02** | `test_db02_concurrent_coordination_number_generation`: 10 simultaneous threads generate 10 unique, collision-free coordination numbers. | `tests.test_v2_database` | **PASSED** | ✅ PASS |
| **DB-03** | `test_db03_prevent_self_referential_relationships`: Database `CheckConstraint` blocks linking a complaint to itself in `CaseRelationship`. | `tests.test_v2_database` | **PASSED** | ✅ PASS |
| **DB-04** | `test_db04_prevent_self_referential_overlap_candidates`: Database `CheckConstraint` blocks linking a complaint to itself in `OverlapCandidate`. | `tests.test_v2_database` | **PASSED** | ✅ PASS |
| **AI-01** | `test_ai01_same_institution_unrelated_issue_distinct`: Two unrelated complaints against the same college trigger Category A alert but NOT issue overlap (Cat B). | `tests.test_v2_intelligence` | **PASSED** | ✅ PASS |
| **AI-02** | `test_ai02_same_institution_related_issue_detected`: Related laboratory deficiencies against same college are detected with substantive semantic overlap. | `tests.test_v2_intelligence` | **PASSED** | ✅ PASS |
| **AI-04** | `test_ai04_tamil_unicode_preservation`: Tamil Unicode characters and combining marks are preserved during normalization and text matching (similarity > 0.4). | `tests.test_v2_intelligence` | **PASSED** | ✅ PASS |
| **AI-05** | `test_ai05_hindi_unicode_preservation`: Hindi Devanagari script characters are preserved and correctly compared. | `tests.test_v2_intelligence` | **PASSED** | ✅ PASS |
| **AI-08** | `test_ai08_human_review_persistence`: Dismissed or confirmed candidate decisions by human officers persist across future engine executions. | `tests.test_v2_intelligence` | **PASSED** | ✅ PASS |
| **AI-09** | `test_ai09_original_complaints_unaffected_by_overlap_decisions`: Confirming an overlap creates `CaseRelationship` but never mutates original complaint status. | `tests.test_v2_intelligence` | **PASSED** | ✅ PASS |
| **WF-01** | `test_wf01_unauthorized_transfer_rejected`: Case officer from another bureau cannot request transfer of another bureau's case (`UnauthorizedWorkflowActionError`). | `tests.test_v2_workflows` | **PASSED** | ✅ PASS |
| **WF-02** | `test_wf02_invalid_status_transition_rejected`: Transitioning directly from PENDING to DISPOSED is blocked by state machine (`WorkflowTransitionError`). | `tests.test_v2_workflows` | **PASSED** | ✅ PASS |
| **WF-03** | `test_wf03_audit_trail_completeness`: Every workflow mutation produces an immutable `AuditEvent` record with actor, timestamp, and delta. | `tests.test_v2_workflows` | **PASSED** | ✅ PASS |
| **WF-04** | `test_wf04_transfer_approval_and_rejection_correctness`: Transfer requires approval from destination bureau head and safely updates handling bureau. | `tests.test_v2_workflows` | **PASSED** | ✅ PASS |
| **REP-01** | `test_rep01_accurate_dashboard_counts`: Dashboard KPIs match direct ORM counts with zero-denominator safety. | `tests.test_v2_reports` | **PASSED** | ✅ PASS |
| **REP-02** | `test_rep02_scoped_filtered_exports`: CSV export filtered by Bureau Head only exports that bureau's cases. | `tests.test_v2_reports` | **PASSED** | ✅ PASS |
| **REP-03** | `test_rep03_empty_data_report_generation`: Empty querysets produce valid CSV and Excel headers without errors. | `tests.test_v2_reports` | **PASSED** | ✅ PASS |
| **REP-04** | `test_rep04_formula_injection_sanitization`: Cells starting with `=`, `+`, `-`, `@`, `\t`, `\r` are sanitized against CSV/Excel formula injection (CWE-1236). | `tests.test_v2_reports` | **PASSED** | ✅ PASS |

---

### Baseline Test Matrix (T01 - T30)

| Scenario ID | Test Method & Description | Module | Result | Status |
|---|---|---|:---:|:---:|
| **T01** | `test_t01_authorized_login_succeeds`: Valid credentials establish authenticated session and redirect to dashboard. | `tests.test_auth_and_roles` | **PASSED** | ✅ PASS |
| **T02** | `test_t02_invalid_login_fails_safely`: Invalid credentials fail safely with error message without leaking user data. | `tests.test_auth_and_roles` | **PASSED** | ✅ PASS |
| **T03** | `test_t03_unauthorized_user_cannot_access_restricted_complaints`: PGRC officer denied access to RB confidential complaint (HTTP 403). | `tests.test_auth_and_roles` | **PASSED** | ✅ PASS |
| **T04A** | `test_t04_duplicate_permanent_id_is_rejected_by_db`: Database unique constraint raises `IntegrityError` on duplicate Permanent ID. | `tests.test_institutions` | **PASSED** | ✅ PASS |
| **T04B** | `test_t04_duplicate_permanent_id_is_rejected_by_form`: Form clean method rejects duplicate Permanent ID with helpful message. | `tests.test_institutions` | **PASSED** | ✅ PASS |
| **T05** | `test_t05_complaint_creation_persists_correctly`: Intake registers complaint with sequential ID and initial `CREATED` action. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T06** | `test_t06_concurrent_complaint_creation_generates_unique_ids`: Sequential/concurrent generator prevents ID collisions. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T07** | `test_t07_officer_assignment_updates_the_correct_case`: Assigning officer updates case and auto-advances PENDING to UNDER_PROCESS. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T08** | `test_t08_invalid_workflow_transition_is_rejected`: State machine transition validation rejects illegal state jumps. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T09** | `test_t09_complaint_transfer_records_complete_history`: Inter-bureau transfer records request, approval, and updates handling bureau. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T10** | `test_t10_escalation_is_visible_and_resolvable_by_competent_authority`: Escalates case and allows Competent Authority to record disposal. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T11** | `test_t11_two_active_cross_bureau_cases_trigger_detection`: Active cases across different bureaus for same institution trigger overlap. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T12** | `test_t12_similar_issue_descriptions_generate_high_similarity_score`: NLP semantic similarity produces high score on related issues. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T13** | `test_t13_different_issues_against_same_institution_distinguished`: Unrelated grievances against same institution produce low similarity score. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T14** | `test_t14_reviewer_can_confirm_a_relationship`: Authorized official confirms overlap, creating `CaseRelationship(CONFIRMED_RELATED)`. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T15** | `test_t15_reviewer_can_reject_false_positive_suggestion`: Reviewer dismisses candidate with audit justification remarks. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T16** | `test_t16_ai_model_failure_does_not_break_normal_complaint_registration`: AI service failure fails safely without disrupting complaint intake. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T17** | `test_t17_overlap_review_never_automatically_closes_complaints`: AI overlap confirmation preserves active complaint status without closing cases. | `tests.test_intelligence_engine` | **PASSED** | ✅ PASS |
| **T18** | `test_t18_coordination_records_preserve_original_case_identities`: Establishing joint coordination retains independent case IDs and histories. | `tests.test_coordination` | **PASSED** | ✅ PASS |
| **T19** | `test_t19_unauthorized_officers_cannot_modify_other_bureau_records`: Enforces mutation boundaries preventing cross-bureau data tampering. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T20** | `test_t20_overdue_case_alerts_work`: `check_sla_breaches` scanner detects expired deadlines and creates `OVERDUE_ALERT`. | `tests.test_sla_and_notifications` | **PASSED** | ✅ PASS |
| **T21** | `test_t21_repeated_scheduler_execution_does_not_generate_duplicate_notifications`: Idempotency logic prevents duplicate alert spam. | `tests.test_sla_and_notifications` | **PASSED** | ✅ PASS |
| **T22** | `test_t22_dashboard_metrics_match_database_records`: Dashboard KPIs match direct ORM counts with zero-denominator safety. | `tests.test_dashboard_and_reports` | **PASSED** | ✅ PASS |
| **T23** | `test_t23_search_filters_return_accurate_results`: Complaint search by ID and title returns precise filtered records. | `tests.test_dashboard_and_reports` | **PASSED** | ✅ PASS |
| **T24** | `test_t24_reports_respect_role_based_access`: CSV report exports apply authenticated user's bureau scope boundaries. | `tests.test_dashboard_and_reports` | **PASSED** | ✅ PASS |
| **T25** | `test_t25_unauthorized_document_downloads_fail`: Private document streaming view raises 403 Forbidden for unauthorized users. | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T26** | `test_t26_invalid_file_uploads_are_rejected`: Extension whitelist blocks disallowed file uploads (.exe). | `tests.test_complaints_workflow` | **PASSED** | ✅ PASS |
| **T27** | `test_t27_responsive_layout_assets_render`: Base layout serves custom design system CSS and JS assets cleanly. | `tests.test_navigation_and_deploy` | **PASSED** | ✅ PASS |
| **T28** | `test_t28_all_primary_navigation_links_resolve`: 13 primary application endpoints resolve successfully (HTTP 200). | `tests.test_navigation_and_deploy` | **PASSED** | ✅ PASS |
| **T29** | `test_t29_forms_show_meaningful_validation_messages`: Form input validation displays field-specific error messages. | `tests.test_navigation_and_deploy` | **PASSED** | ✅ PASS |
| **T30** | `test_t30_production_deployment_configuration_check`: Django system checks and production settings pass without errors. | `tests.test_navigation_and_deploy` | **PASSED** | ✅ PASS |

---

### Command Output Summary

```text
Creating test database for alias 'default'...
..................SentenceTransformer not available or model load deferred: No module named 'sentence_transformers'. Falling back to TF-IDF.
.......................................
----------------------------------------------------------------------
Ran 57 tests in 71.121s

OK
Destroying test database for alias 'default'...
Found 57 test(s).
System check identified no issues (0 silenced).
```

