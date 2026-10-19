# MITRC LibSphere

> **Prototype name:** LibSpace  
> **Website / project name:** LibSphere

**Discover • Borrow • Suggest • Learn**

A prototype Library Management & Discovery Portal for the Modern Institute of Technology and Research Centre (MITRC), Alwar, Rajasthan. Built as a college internal hackathon project.

> **Status: Prototype implementation in progress.** The React/Vite frontend talks to the Flask API. Use the isolated SQLite seed database for local testing; PostgreSQL remains the intended deployment database and has not been verified locally.

## 1. Overview
LibSphere digitizes the complete library lifecycle:

```text
Discover → Search → Request / Reserve → Librarian Approval → Issue
→ Borrow → Return → Suggest → Community Vote → Acquisition → Analytics
```

It is meant to feel like a real institutional product rather than a CRUD assignment.

## 2. Problem Statement
Students and faculty struggle to discover books, know whether copies are available, find where a book sits, track due dates, and influence what the library buys. Librarians lack a single place for loans, returns, reservations, demand insight, and audit history.

## 3. Solution
A web portal where users search the catalogue, see live availability and rack/shelf location, request/borrow/reserve books, receive in-app notifications, suggest new books and vote on suggestions; and where librarians manage inventory, loans, suggestions, reports and audit logs.

## 4. Features
- **Implemented prototype workflows:** local testing login, role-specific dashboards, paginated/filterable catalogue search, student/faculty borrowing requests, librarian review/approval/issue, requested-books status, suggestion voting, and department analytics filters.
- **Seeded domain models/data:** departments, users, books, copies, workflow history, votes, notifications, fines, and audit events. Reservations, returns, fines, and audit entries do not all have complete interactive workflows.
- **Future scope:** AI recommendations, natural-language search, email notifications, library map, PWA/mobile, college SSO.

## 5. User Roles
`STUDENT`, `FACULTY`, `DEPARTMENT`, `LIBRARIAN`, `ADMIN` — see [roles and permissions](docs/07-security/authorization-rbac.md).

## 6. Technology Stack
| Layer | Technology |
|---|---|
| Frontend | React, JavaScript (not TypeScript), Vite, Tailwind CSS |
| Backend | Flask, Python |
| Database | SQLite for local development and testing; PostgreSQL support remains future deployment scope |
| Containers | Docker Compose (planned; must not delay core work) |

## 7. Architecture
```text
React (HTTP/JSON) → Flask API → SQLAlchemy → SQLite (testing) / PostgreSQL (deployment)
```
The frontend never connects directly to PostgreSQL. See [system architecture](docs/03-architecture/system-architecture.md).

## 8. Planned Directory Structure
```text
MITRC-LibSphere/
├── docs/        project knowledge and engineering documentation
├── frontend/    React user interface
├── backend/     Flask API and business logic
├── database/    PostgreSQL schema, migrations and seed data
├── scripts/     setup / automation / backup
└── tests/       integration and end-to-end verification
```
Only these directories plus `.env.example`, `.gitignore`, `docker-compose.yml` and `README.md` belong in the first milestone; everything else is created progressively.

## Local SQLite testing (Windows PowerShell)

SQLite is the sole database used by the current local development and testing workflow. Persistent testing data is stored in `backend/instance/libsphere_test.db`; the local-development default is `backend/instance/libsphere.db`. Flask resolves relative SQLite URLs beneath its instance directory. The checked-in legacy seed catalog has blank ISBNs and is retained only for isolated in-memory tests. File-backed `seed_test_db.py` refuses a fresh database without an ISBN-backed source and returns without row upserts when an existing persistent catalog is present; it never resets or reseeds persistent data.

1. From the repository root, create the backend virtual environment if needed and install dependencies:

   ```powershell
   py -3 -m venv .\backend\.venv
   $python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
   & $python -m pip install -r .\backend\requirements.txt
   ```

2. The old JSON fixture is not a safe source for fresh file-backed seeding. Do not run `--reset` or invoke `seed_test_db.py` to repopulate the persistent testing DB. Automated tests use an isolated in-memory SQLite database and may load the legacy fixture there. For a new persistent catalogue, first use the reviewed academic CSV preflight/import workflow in `HOW_TO_RUN.md`; that import does not create copies or demo user accounts.

3. Start the backend in a PowerShell window:

   ```powershell
   Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
   $env:APP_ENV = 'testing'
   $env:DATABASE_URL = 'sqlite:///libsphere_test.db'
   $env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
   $env:JWT_SECRET_KEY = ([guid]::NewGuid().ToString() + [guid]::NewGuid().ToString())
   & $python .\backend\app.py
   ```

4. Start the frontend in another PowerShell window (the testing mode exposes only the three-field demo form):

   ```powershell
   $env:VITE_API_URL = 'http://localhost:5001'
   $env:VITE_AUTH_MODE = 'testing'
   .\scripts\run_frontend.ps1
   ```

5. Open `http://127.0.0.1:5173` and check `http://127.0.0.1:5001/api/health`. Demo identities (no passwords; valid only while the backend has `APP_ENV=testing`):

   | Name | User ID | Role |
   |---|---|---|
   | Urvashi | `25EMCAD016` | `STUDENT` |
   | Yashdeep | `25TECAD016` | `FACULTY` (UI label: Teacher) |
   | Dhruv | `25DMCAD016` | `DEPARTMENT` |
   | Sphere | `25LIB016` | `LIBRARIAN` |

   This is deliberately passwordless test authentication, not identity verification. The frontend shows this three-field form only when `VITE_AUTH_MODE=testing`; otherwise it displays no login fields. The backend accepts the seeded profiles only while `APP_ENV=testing`. Existing production API authentication remains unchanged and does not accept this passwordless flow.

The isolated in-memory test fixture contains 119 legacy titles and generated demo copies solely for automated tests; it does not describe the live file-backed catalogue. The active test SQLite file is the separate imported/curated catalogue documented in `HOW_TO_RUN.md`. The academic import did not create physical copies or modify seeded user/workflow counts.

### Department testing accounts

| Department | User ID |
|---|---|
| B.Tech - CSE | `25DMCAD016` (Dhruv) |
| B.Tech - AI&DS | `DEPT-AIDS` |
| B.Tech - AI&ML | `DEPT-AIML` |
| B.Tech - Mechanical | `DEPT-MECH` |
| B.Tech - Electrical | `DEPT-ELEC` |
| B.Tech - Civil | `DEPT-CIVIL` |
| BBA | `DEPT-BBA` |
| BCA | `DEPT-BCA` |
| M.Tech | `DEPT-MTECH` |

The exact testing profile accounts required by the brief are included within those totals. Names/IDs are case-insensitive at login; surrounding whitespace is trimmed, while internal ID whitespace and punctuation are preserved and therefore do not match a canonical ID.

## PostgreSQL deployment configuration (future)

PostgreSQL remains the intended deployment database. Set `APP_ENV=production`, configure `DATABASE_URL` with the deployment PostgreSQL URI, and provide a unique secret `JWT_SECRET_KEY` outside the repository. Never point a testing command at a production URL. The legacy `database/schema/schema.sql` setup can drop/recreate tables; run it only on a disposable local PostgreSQL database after reviewing it, never on shared or production data. PostgreSQL connectivity has not been verified in this local environment.

The backend uses Flask on `http://127.0.0.1:5001`; Vite uses `http://127.0.0.1:5173` for the local testing launcher. The frontend only talks to the Flask API, never to either database. `VITE_API_URL` selects the API base URL. `npm run build` builds the frontend from `frontend/`.

## Testing

Run the backend suite from the repository root:

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
& $python -m unittest discover -s tests -v
```

The backend tests use an isolated SQLite test database; the separate seed command above initializes the persistent local test file. Run `npm run verify:virtual-grid` from `frontend/` for a repeatable initial-render measurement: the current component produced 15 visible/overscan cards from 1,000 inputs (1.5%) in its server-rendered initial window. This is not a browser scrolling or runtime performance profile. The API health endpoint reports success only when the configured database is reachable and the required tables exist.


## 14. Demo
See [end-to-end demo flow](docs/09-workflows/end-to-end-demo-flow.md).

## 15. Contribution
See [git workflow](docs/12-development/git-workflow.md) and [commit conventions](docs/12-development/commit-conventions.md).

## 16. License
*To be decided.* (`LICENSE` file not yet created.)

## 17. Future Scope
See [future scope](docs/15-project-management/future-scope.md).
