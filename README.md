# AUGIS – AICTE Unified Grievance Intelligence System
### *Statement 2: Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells*

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1%20%7C%206.1-green.svg)](https://www.djangoproject.com/)
[![Database](https://img.shields.io/badge/PostgreSQL-Supported-336791.svg)](https://www.postgresql.org/)
[![AI Engine](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-blueviolet.svg)](https://ai.google.dev/)
[![2FA Auth](https://img.shields.io/badge/2FA-Email%20OTP%20Verified-success.svg)]()
[![E2E Tests](https://img.shields.io/badge/Playwright-10%2F10%20Passing-brightgreen.svg)]()
[![Unit Tests](https://img.shields.io/badge/Django%20Tests-60%2F60%20Passing-brightgreen.svg)]()

> **Notice**: AUGIS is an enterprise-grade prototype implementation of the **All India Council for Technical Education (AICTE)** Problem Statement 2 for unified institution grievance monitoring, cross-bureau coordination, and AI-assisted overlap detection.

---

## 1. Executive Summary & Problem Statement Alignment

### The Core Problem (AICTE Problem Statement 2)
The All India Council for Technical Education (AICTE) receives various complaints and grievances related to technical education institutions from students, faculty members, parents, and stakeholders. These complaints are handled by different Bureaus and Cells, primarily:
- **Regulation Bureau (RB)**: Deals with affiliation norms, infrastructure deficits, unapproved courses, land norms, and regulatory violations.
- **Public Grievance Redressal Cell (PGRC)**: Handles student petitions, faculty salary arrears, capitation fee disputes, and certificate withholding.
- **Approval Bureau (AB)**: Manages annual intake approvals and operational compliance.
- **Regional Offices (RO)**: Oversee localized inspections, geographical jurisdictions, and field inquiries.

**The Failure Mode**: Cases relating to the same institution were received and processed independently by different Bureaus. Due to the absence of a centralized, real-time mechanism, AICTE experienced:
- **Overlapping actions & duplication of effort**: Multiple bureaus conducting independent inspections on the same college.
- **Contradictory orders**: One bureau approving expansion while another was initiating penal action.
- **Delays in disposal**: Bureau hopping and difficulty identifying who was actively handling the institution.
- **Fragmented institutional history**: Inability to view all historical and concurrent cases for a single college in one place.

### The AUGIS Solution
AUGIS establishes a **Single Source of Truth** for institution-related complaints across all AICTE Bureaus:
1. **Centralized Institution Profile**: Complete docket indexed by unique **AICTE Permanent ID**, containing address, district, state, operational status, and consolidated grievance history.
2. **Comprehensive Complaint Tracking (14 AICTE Mandatory Fields)**: Unique Complaint No, Date of Receipt, Grievance Classification, Priority, Current Status, Presently Assigned Bureau, Assigned Case Officer, Last Action Taken, Date & Time of Last Action, Next Action Required, Resolution SLA Deadline, Supporting Documents, and Transfer/Escalation History.
3. **Cross-Bureau Overlap Detection**: Smart algorithmic matching that alerts officials when complaints concerning the same institution are active across RB, PGRC, and other cells. Displays clear notice: **`"Potential Overlapping Cases – Coordination Required"`**.
4. **Google Gemini AI Scrutiny**: Integrates official **Google Gemini AI** (`gemini-2.5-flash`) via the `google-genai` SDK to semantically compare grievance descriptions, compute conflict risk, and generate actionable joint coordination recommendations.
5. **Real-Time Executive Dashboard**: 12 KPI metrics (Total Received, Pending Intake, Under Process, Disposed, Transferred, Escalated, Overdue Breaches, Overlap Clusters) with interactive Chart.js visualizations.
6. **Statutory Analytics & Audit Reports**: 9 specialized report types (Bureau-Wise, Region-Wise, Institution-Wise, Status-Wise, Ageing Analysis, Disposal Rate, Overlap Cases, Monthly Performance, Quarterly Review) with instant CSV, Excel, and PDF exports.
7. **Two-Factor Authentication (2FA OTP)**: Mandatory 6-digit OTP verification delivered via Gmail/SMTP for all user roles.

---

## 2. Quickstart Guide: 1-Click Launch with `start.bat`

### Windows (Recommended)
Double-click **`start.bat`** in the project root or run from command prompt:
```bat
start.bat
```
`start.bat` automatically:
1. Detects and activates the Python virtual environment (`.venv`).
2. Installs or updates dependencies from `requirements.txt`.
3. Runs all pending database migrations (`manage.py migrate`).
4. Compiles and collects static files (`manage.py collectstatic --noinput`).
5. Opens your default web browser to `http://127.0.0.1:8000`.
6. Launches the Django server on `http://127.0.0.1:8000`.

### Manual Startup (Cross-Platform)
```bash
# 1. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. Run migrations
python manage.py migrate

# 3. Collect static files
python manage.py collectstatic --noinput

# 4. Start server
python manage.py runserver 127.0.0.1:8000
```
Navigate to `http://127.0.0.1:8000/accounts/login/`.

---

## 3. Pre-Configured Demonstration Accounts

All pre-configured demonstration accounts use the password: **`Augis@2026`**

| Role | Username | Password | Operational Scope & Jurisdiction |
|---|---|---|---|
| **Super Administrator** | `admin` | `Augis@2026` | Full administrative control, system settings, global audit logs, full access. |
| **Bureau Head (RB)** | `rb_head` | `Augis@2026` | Regulation Bureau head: case distribution, inter-bureau coordination, overlap approval. |
| **Case Officer (RB)** | `rb_officer` | `Augis@2026` | Regulation Bureau investigator: inspections, evidence notes, status transitions. |
| **Bureau Head (PGRC)** | `pgrc_head` | `Augis@2026` | Public Grievance Redressal Cell head: student/faculty petition synergy. |
| **Case Officer (PGRC)** | `pgrc_officer` | `Augis@2026` | PGRC investigator: student grievance hearings, fee refund inquiries. |
| **Regional Officer (North)** | `ro_north` | `Augis@2026` | Northern region jurisdictional oversight (Delhi, UP, Haryana, Punjab, etc.). |
| **Regional Officer (South)** | `ro_south` | `Augis@2026` | Southern region jurisdictional oversight (Tamil Nadu, Karnataka, Kerala, etc.). |
| **Senior Management** | `senior_mgmt` | `Augis@2026` | Member Secretary / Advisor: executive oversight, national KPI monitoring. |
| **Competent Authority** | `competent_auth` | `Augis@2026` | AICTE Chairman / Vice Chairman: binding decisions on escalations and joint dockets. |

---

## 4. Two-Factor Authentication (Email / Gmail OTP 2FA)

Security compliance mandates two-factor verification for all AICTE administrative users.

### How 2FA Works
1. User enters valid username and password on `/accounts/login/`.
2. System securely validates credentials, sets pre-auth session, generates a cryptographically random 6-digit OTP code with a 10-minute expiry window, and redirects to `/accounts/verify-otp/`.
3. The 6-digit code is dispatched to the user's registered email address.
4. **Local Development / Demo Mode**: If Gmail SMTP is not configured, the generated OTP code is displayed directly in the green informational flash banner on the verification page for seamless testing.
5. Entering the valid OTP logs the user into their scoped dashboard.

### Configuring Real Gmail SMTP (Production)
In your `.env` file, configure your Gmail account and App Password:
```env
AUTH_2FA_ENABLED=True
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password
DEFAULT_FROM_EMAIL=AICTE Security <your_email@gmail.com>
```
*(To generate a Gmail App Password: Go to Google Account Settings -> Security -> 2-Step Verification -> App Passwords -> Generate).*

---

## 5. Google Gemini AI Deep Scrutiny Engine

AUGIS integrates Google Gemini AI (`gemini-2.5-flash`) via Google's official `google-genai` SDK to automate cross-bureau intelligence analysis.

### Features of the Gemini AI Scrutiny Engine
- **Cross-Bureau Overlap Identification**: Evaluates whether two complaints filed against the same college in separate bureaus (e.g. PGRC vs Regulation Bureau) stem from common root causes (e.g. unapproved faculty leading to both student grading disputes and statutory norm breaches).
- **Inter-Bureau Conflict Risk**: Categorizes risk (`HIGH`, `MEDIUM`, `LOW`) of conflicting decisions or redundant inspections.
- **Actionable Coordination Recommendations**: Generates concrete steps, such as establishing a joint inspection committee or designating a lead bureau.
- **Smart Local Fallback**: When `GEMINI_API_KEY` is not present, the system seamlessly transitions to a deterministic rule-based semantic analyzer so the application never breaks.

### Enabling Live Gemini AI (Google AI Studio)
1. Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2. Add your key to `.env`:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
3. Visit any Overlap Candidate under **Intelligence -> Overlap Intelligence Center -> Inspect Candidate Dossier**, and click **`Run Fresh AI Scrutiny`**.

---

## 6. Authentic Tamil Nadu Engineering Colleges Registry

To reflect real-world AICTE operations, the database includes authentic Tamil Nadu technical institutions with genuine AICTE Permanent IDs, districts, and realistic cross-bureau dockets:

| AICTE Permanent ID | Institution Name | District | Region | Sample Active Dockets |
|---|---|---|---|---|
| **`1-4165514`** | PSG College of Technology | Coimbatore | SOUTHERN | Infrastructure norm review (RB) & Lab equipment fee dispute (PGRC) |
| **`1-1229101`** | SSN College of Engineering | Chengalpattu | SOUTHERN | Faculty cadre ratio verification (RB) & Student hostel amenities petition (PGRC) |
| **`1-4822001`** | College of Engineering Guindy, Anna University | Chennai | SOUTHERN | Special course affiliation review (AB) |
| **`1-429823423`** | Thiagarajar College of Engineering | Madurai | SOUTHERN | Autonomy curriculum compliance (RB) & Examination schedule grievance (PGRC) |
| **`1-4221764`** | Coimbatore Institute of Technology (CIT) | Coimbatore | SOUTHERN | Faculty cadre compliance (RB) |
| **`1-4554801`** | Government College of Technology (GCT) | Coimbatore | SOUTHERN | Campus development grant utilization (RO) |
| **`1-5021489`** | Madras Institute of Technology (MIT Chromepet) | Chennai | SOUTHERN | Aeronautical laboratory compliance (RB) |
| **`1-401662465`** | Kongu Engineering College | Erode | SOUTHERN | Land use norms inquiry (RB) & Transportation fee refund petition (PGRC) |
| **`1-4389101`** | Kumaraguru College of Technology | Coimbatore | SOUTHERN | Faculty recruitment qualification scrutiny (RB) |
| **`1-4491024`** | National Engineering College | Kovilpatti | SOUTHERN | Anti-ragging committee constitution review (PGRC) |
| **`1-4712019`** | Mepco Schlenk Engineering College | Sivakasi | SOUTHERN | Research grant fund allocation review (RB) |
| **`1-4629811`** | SRM Valliammai Engineering College | Chengalpattu | SOUTHERN | Mandatory disclosure compliance audit (RB) |
| **`1-4560123`** | Bannari Amman Institute of Technology | Erode | SOUTHERN | Green campus environmental compliance (RB) |
| **`1-7030281`** | Annapoorana Engineering College | Salem | SOUTHERN | Approval extension review (AB) & Fee concession petition (PGRC) |
| **`1-4401459`** | KCG College of Technology | Chennai | SOUTHERN | Aviation laboratory equipment inspection (RB) |

*Search by college name, AICTE Permanent ID, or district on `/institutions/` to view the unified 360° dossier.*

---

## 7. How to Deploy on Vercel (100% Free Tier)

AUGIS is configured for serverless deployment on the **Vercel Free Tier** using `vercel.json` and `wsgi_vercel.py`.

### Prerequisites
1. A free GitHub account.
2. A free [Vercel](https://vercel.com/) account.
3. A free PostgreSQL database instance from [Neon.tech](https://neon.tech/) or [Supabase.com](https://supabase.com/).

### Step-by-Step Deployment Runbook

#### Step 1: Create Free PostgreSQL Database
1. Go to [Neon.tech](https://neon.tech/) and create a free serverless PostgreSQL database.
2. Copy your Connection String (`DATABASE_URL`), for example:
   ```text
   postgres://username:password@ep-sample-12345.ap-southeast-1.aws.neon.tech/augis_db?sslmode=require
   ```

#### Step 2: Push Repository to GitHub
```bash
git init
git add .
git commit -m "AUGIS Enterprise AICTE Complaint Monitoring System"
git branch -M main
git remote add origin https://github.com/your-username/augis-aicte.git
git push -u origin main
```

#### Step 3: Deploy to Vercel
1. Log in to [Vercel](https://vercel.com/) and click **"Add New" -> "Project"**.
2. Select your GitHub repository (`augis-aicte`) and click **"Import"**.
3. In **Build and Output Settings**:
   - Framework Preset: **Other**
   - Root Directory: `./`
4. Under **Environment Variables**, add:
   | Variable Name | Value | Note |
   |---|---|---|
   | `DJANGO_SETTINGS_MODULE` | `config.settings.production` | Enables production settings |
   | `SECRET_KEY` | *(generate a 50-character random string)* | Production Django secret |
   | `DEBUG` | `False` | Disables debug mode |
   | `DATABASE_URL` | *(your Neon/Supabase PostgreSQL URL)* | Free cloud PostgreSQL |
   | `GEMINI_API_KEY` | *(your Google AI Studio API key)* | Optional for live AI |
   | `AUTH_2FA_ENABLED` | `True` | 2FA OTP verification |
   | `EMAIL_HOST_USER` | `your_email@gmail.com` | Optional Gmail sender |
   | `EMAIL_HOST_PASSWORD` | `your_gmail_app_password` | Optional Gmail password |
5. Click **"Deploy"**. Vercel will run `build_files.sh`, collect all static files, and deploy the serverless WSGI handler.

#### Step 4: Run Initial Production Migrations & Seed Data
You can run migrations against your Neon/Supabase database directly from your local terminal:
```bash
# In your local terminal, temporarily point DATABASE_URL to your Neon cloud DB:
set DATABASE_URL=postgres://username:password@ep-sample-12345.ap-southeast-1.aws.neon.tech/augis_db?sslmode=require
python manage.py migrate
python manage.py seed_augis_demo
python scripts/seed_tamil_nadu_colleges.py
```
Your live Vercel application is now fully deployed with pre-seeded data, ready for evaluation!

---

## 8. Technology Stack & Architecture

- **Backend**: Python 3.12, Django 6.1.2 (Strictly No React, No Next.js, No Node.js).
- **Frontend**: Django Template Language, Bootstrap 5.3, HTMX 1.9, Chart.js 4.4, Bootstrap Icons.
- **Database**: PostgreSQL 16 (with SQLite local zero-config fallback).
- **AI & NLP**: Google Gemini 2.5 Flash (`google-genai`), Scikit-Learn (TF-IDF & Cosine Similarity).
- **Exports & Reporting**: ReportLab (Vector PDF), OpenPyXL (Excel), CSV streaming.
- **Security**: Email OTP 2FA (`EmailOTP`), PBKDF2 Password Hashing, CSRF Tokens, Secure Session Cookies, Object-Level RBAC Scoping, Immutable Audit Logging (`AuditEvent`).

---

## 9. Verification & Test Suite Results

AUGIS includes comprehensive test coverage across both unit/integration tests and automated browser end-to-end tests:

### Automated Browser End-to-End Test (Playwright)
Run the Playwright smoke test:
```powershell
python scripts/playwright_smoke_test.py
```
**Results (10/10 PASS - 100%)**:
```text
===========================================================================
AUGIS PLAYWRIGHT END-TO-END BROWSER VERIFICATION SUITE
Target Server: http://127.0.0.1:8000
===========================================================================
[PASS] Dashboard & 2FA Login            : 2FA OTP + All 12 metrics displayed correctly
[PASS] Multi-Criteria Search & Filter   : Priority, Region, Date Range, Status filters verified
[PASS] Institution 360° Dossier         : Permanent ID, full profile, interactive status tabs verified
[PASS] Complaint 14-Field Tracking      : All fields & next_action_required verified
[PASS] Overlap Detection & Alerts       : Category A & B detection, alerts, and coordination links verified
[PASS] Coordination Workspace           : Inter-bureau docket and lead bureau tracking verified
[PASS] Statutory Analytics Reports      : All 9 report views and PDF/Excel/CSV exports verified
[PASS] Role-Based Access Control        : ro_north scoped strictly to NORTHERN jurisdiction (41 cases)
[PASS] Tamil Nadu Registry              : PSG College of Technology (1-4165514) verified
[PASS] Google Gemini AI Scrutiny        : AI synthesis, conflict analysis, and recommendations verified
===========================================================================
```

### Automated Django Test Suite (Unit & Integration)
Run the Django test runner:
```powershell
python manage.py test tests
```
**Results (60/60 PASS - 100%)**:
```text
Ran 60 tests in 70.287s
OK
System check identified no issues (0 silenced).
```

---

## 10. Complete Documentation Sitemap

Detailed architectural and regulatory documentation files:
- [REQUIREMENTS.md](REQUIREMENTS.md) — Requirements Traceability Matrix (RTM) against AICTE Problem Statement 2
- [ARCHITECTURE.md](ARCHITECTURE.md) — High-Level Architecture, Monolithic Design & Data Flow
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — PostgreSQL Schema, Entity Relations & Indexing Strategy
- [USER_ROLES.md](USER_ROLES.md) — RBAC Scoping, Permission Matrix & Regional Jurisdictions
- [WORKFLOW_RULES.md](WORKFLOW_RULES.md) — Complaint Lifecycle State Machine & Transition Rules
- [AI_MATCHING_ENGINE.md](AI_MATCHING_ENGINE.md) — Google Gemini AI & Hybrid Deterministic Overlap Engine
- [SECURITY.md](SECURITY.md) — 2FA OTP Architecture, Document Vault & Tamper-Evident Audit Logging
- [DEPLOYMENT.md](DEPLOYMENT.md) — Production Runbook (Vercel, Docker, Gunicorn, WhiteNoise)
