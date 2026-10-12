# MITRC LibSphere

> **Prototype name:** LibSpace  
> **Website / project name:** LibSphere

**Discover • Borrow • Suggest • Learn**

A Library Management & Discovery Portal for the Modern Institute of Technology and Research Centre (MITRC), Alwar, Rajasthan. Built as a college internal hackathon project.

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
- **MVP:** authentication, role-based dashboards, catalogue, search/filter/sort, availability, physical copies, borrow/return, suggestions, voting, librarian dashboard, in-app notifications.
- **Strong enhancements:** reservations, waiting list, fines, analytics, audit logs.
- **Future scope:** AI recommendations, natural-language search, email notifications, library map, PWA/mobile, college SSO.

## 5. User Roles
`STUDENT`, `FACULTY`, `DEPARTMENT`, `LIBRARIAN`, `ADMIN` — see [roles and permissions](docs/07-security/authorization-rbac.md).

## 6. Technology Stack
| Layer | Technology |
|---|---|
| Frontend | React, JavaScript (not TypeScript), Vite, Tailwind CSS |
| Backend | Flask, Python |
| Database | SQLite for local testing; PostgreSQL for future deployment |
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

SQLite is a local testing option only. The database file is `backend/instance/libsphere_test.db`; Flask resolves the relative SQLite URL beneath its instance directory. The seed command explicitly selects SQLite and ignores `DATABASE_URL` from `.env`, so it will not connect to PostgreSQL. Seeding is repeatable and does not reset data unless `--reset` is explicitly supplied.

1. From the repository root, create the backend virtual environment if needed and install dependencies:

   ```powershell
   py -3 -m venv .\backend\.venv
   $python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
   & $python -m pip install -r .\backend\requirements.txt
   ```

2. Initialize and seed the local SQLite database (safe to rerun; does not delete the existing database):

   ```powershell
   Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
   $env:APP_ENV = 'testing'
   $env:DATABASE_URL = 'sqlite:///libsphere_test.db'
   & $python .\backend\seed_test_db.py
   ```

   To explicitly recreate only this SQLite test database, run:

   ```powershell
   & $python .\backend\seed_test_db.py --reset
   ```

   The seeder rejects non-SQLite URLs and database files outside `backend/instance/`. It never drops or alters PostgreSQL.

3. Start the backend in a PowerShell window:

   ```powershell
   Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
   $env:APP_ENV = 'testing'
   $env:DATABASE_URL = 'sqlite:///libsphere_test.db'
   $env:CORS_ORIGINS = 'http://localhost:5174,http://127.0.0.1:5174'
   $env:JWT_SECRET_KEY = ([guid]::NewGuid().ToString() + [guid]::NewGuid().ToString())
   & $python .\backend\app.py
   ```

4. Start the frontend in another PowerShell window (the testing mode exposes only the three-field demo form):

   ```powershell
   $env:VITE_API_URL = 'http://localhost:5001'
   $env:VITE_AUTH_MODE = 'testing'
   .\scripts\run_frontend.ps1
   ```

5. Open `http://127.0.0.1:5174` and check `http://127.0.0.1:5001/api/health`. Demo identities (no passwords; valid only while the backend has `APP_ENV=testing`):

   | Name | User ID | Role |
   |---|---|---|
   | Urvashi | `25EMCAD016` | `STUDENT` |
   | Yashdeep | `25TECAD016` | `FACULTY` (UI label: Teacher) |
   | Dhruv | `25DMCAD016` | `DEPARTMENT` |
   | Sphere | `25LIB016` | `LIBRARIAN` |

   This is deliberately passwordless test authentication, not identity verification. The frontend shows this three-field form only when `VITE_AUTH_MODE=testing`; otherwise it displays no login fields. The backend accepts the seeded profiles only while `APP_ENV=testing`. Existing production API authentication remains unchanged and does not accept this passwordless flow.

The data catalog contains 119 distinct titles. Each catalog item has an Open Library work reference; ISBN, edition and other optional metadata are omitted where an edition-level fact was not verified. The seed creates authors, categories, verified known publisher links, departments, 238 copies, workflow records, votes, notifications, fines and audit events. Dashboard figures are calculated from those database rows.

## PostgreSQL deployment configuration (future)

PostgreSQL remains the intended deployment database. Set `APP_ENV=production`, configure `DATABASE_URL` with the deployment PostgreSQL URI, and provide a unique secret `JWT_SECRET_KEY` outside the repository. Never point a testing command at a production URL. The legacy `database/schema/schema.sql` setup can drop/recreate tables; run it only on a disposable local PostgreSQL database after reviewing it, never on shared or production data. PostgreSQL connectivity has not been verified in this local environment.

The backend uses Flask on `http://127.0.0.1:5001`; Vite uses `http://127.0.0.1:5174` for the local testing launcher. The frontend only talks to the Flask API, never to either database. `VITE_API_URL` selects the API base URL. `npm run build` builds the frontend from `frontend/`.

## Testing

Run the backend suite from the repository root:

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
& $python -m unittest discover -s tests -v
```

The tests use an in-memory SQLite database; the separate seed command above initializes the persistent local test file. The API health endpoint reports success only when the configured database is reachable and the required tables exist.


## 14. Demo
See [end-to-end demo flow](docs/09-workflows/end-to-end-demo-flow.md).

## 15. Contribution
See [git workflow](docs/12-development/git-workflow.md) and [commit conventions](docs/12-development/commit-conventions.md).

## 16. License
*To be decided.* (`LICENSE` file not yet created.)

## 17. Future Scope
See [future scope](docs/15-project-management/future-scope.md).
