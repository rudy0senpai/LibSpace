# LibSphere Project Guide

**Status:** Prototype implementation in progress. Updated 2026-10-15. This guide distinguishes automated SQLite test evidence from persistent-file/browser verification.

## Project Overview
LibSphere is a library management/discovery prototype for catalogue search, circulation, suggestions/voting, and role-specific dashboards. Preserve existing React + Flask architecture and do not migrate frameworks without an explicit task.

## Technology Stack
- Frontend: React 18, JavaScript, Vite 5; dependencies include Recharts and lucide-react (`frontend/package.json`).
- Backend: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, python-dotenv (`backend/requirements.txt`).
- ORM/database: SQLAlchemy; persistent SQLite is the sole local development/testing database. PostgreSQL-oriented model support remains future deployment scope and has not been verified here.
- Local backend URL: `http://localhost:5001`; testing frontend launcher uses `http://127.0.0.1:5173` (README/script). Default Vite port may be 5173 outside that launcher.

## Repository Structure and Entry Points
- `backend/app.py`: Flask app, API routes and report queries.
- `backend/config.py`: app/database/JWT config; `backend/identity.py`: canonical testing identity.
- `backend/models.py`: SQLAlchemy entities and enums.
- `backend/seed_test_db.py`: repeatable SQLite test seeder; catalog at `database/seed/books_catalog.json`.
- `backend/instance/libsphere_test.db`: persistent test DB; preserve it unless reset is explicitly requested.
- `frontend/src/pages/`: auth, student, department, librarian views; `context/`, `services/`, `routes/`, `styles/` support the UI.
- `scripts/run_backend.ps1`, `scripts/run_frontend.ps1`: Windows local launchers.
- `tests/test_backend_contract.py`, `tests/test_sqlite_seed.py`: Python unittest suites.
- `docs/`: requirements, architecture, APIs, security, workflows and development documentation.

## Architecture and API Contracts
Frontend calls Flask JSON APIs through `frontend/src/services/api.js` and `authService.js`; it must not access the database directly. API errors use `{status:"error",error:{code,message}}`; successful responses generally use `{status:"success",data:...}`.

Inspected routes in `backend/app.py`: `GET /api/health`; `POST /api/auth/login`; `GET /api/auth/me`; `GET /api/books/search`; `GET /api/categories`; `GET /api/reports/department/dashboard`; `GET /api/reports/librarian/dashboard`; `GET /api/users/me/loans`; `POST /api/users/me/loans/requests`; `GET /api/librarian/loan-requests`; `POST /api/librarian/loan-requests/<loan_id>/review`; `POST /api/librarian/loan-requests/<loan_id>/issue`; `POST /api/users/me/loans/<loan_id>/cancel`; `GET /api/users/me/suggestions`; `POST /api/suggestions`; and `POST /api/suggestions/<suggestion_id>/vote`. Login accepts `{name,user_id,role}` only in testing mode and returns JWT/user data. Protected APIs authorize from the database-backed authenticated account. No logout route was found. Reservation, return, fine payment, audit browsing, and notification-center workflows are not complete API/UI features.

## Roles and Permissions
Enum values: `STUDENT`, `FACULTY`, `DEPARTMENT`, `LIBRARIAN`, `ADMIN`. Department dashboard route permits department, librarian, and admin, and scopes a department user to its associated department. Librarian summary route has its own role gate. Other permissions must be checked at each endpoint; do not infer them from UI navigation.

## Database Schema and Seeding
Entities in `backend/models.py`: Department, User, Publisher, Category, Author, Book, BookCopy, Loan, Reservation, Suggestion, SuggestionVote, Notification, Fine, AuditLog; association tables include book-author and book-department links. Loan/copy/reservation/suggestion states are enums. User identifier columns are `enrollment_id` (student) and `employee_id` (other roles); user has email/password_hash, role, department association, active flag and timestamps. Foreign-key enforcement is enabled for SQLite.

Seed command (from repository root, PowerShell):
```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
& $python .\backend\seed_test_db.py
```
Seeder creates schema in persistent `backend/instance`, rejects non-SQLite URLs, and is repeatable without resetting data; `--reset` explicitly deletes only the selected test SQLite file and WAL/SHM sidecars. Automated tests verify exactly 100 STUDENT, 30 FACULTY, 9 DEPARTMENT and 2 LIBRARIAN accounts (141 total), all requested departments, canonical user-ID uniqueness, and at least 100 distinct titles (catalog has 119). Persistent-file counts/integrity were not queried in this task.

Department account map: B.Tech - CSE=`25DMCAD016` (Dhruv), B.Tech - AI&DS=`DEPT-AIDS`, B.Tech - AI&ML=`DEPT-AIML`, B.Tech - Mechanical=`DEPT-MECH`, B.Tech - Electrical=`DEPT-ELEC`, B.Tech - Civil=`DEPT-CIVIL`, BBA=`DEPT-BBA`, BCA=`DEPT-BCA`, M.Tech=`DEPT-MTECH`. Existing ECE/MBA department rows are retained to preserve relationships. Required demo identities: Urvashi/`25EMCAD016`/STUDENT; Yashdeep/`25TECAD016`/FACULTY; Dhruv/`25DMCAD016`/DEPARTMENT; Sphere/`25LIB016`/LIBRARIAN. All are testing identities, not verified MITRC personnel.

## Features: Verified vs Incomplete
- Implemented and covered by backend tests: case-insensitive local test login with trim-only canonicalization (`TEACHER` aliases `FACULTY`); exact 141-account/nine-department seed; database-backed borrowing request/librarian review/issue and user-scoped loans; server-paginated catalogue search; filtered/scoped department reports; idempotent suggestion voting with current-user state.
- Frontend code includes Requested Books for student/faculty dashboard experience, a librarian request queue, visible-row book virtualization, vote feedback, and department filters/loading/error/retry/reset. Browser end-to-end and visual verification remain outstanding.
- Department navigation destinations not implemented are disabled and labeled unavailable; `Print Report` opens the browser print dialog. Reservations, return/renewal, fine payments, notification center, audit browsing, and report export are not complete interactive workflows.
- No virtualization speedup is claimed. The repeatable `npm run verify:virtual-grid` server-render smoke check measured 15 of 1000 cards in the initial 600px/3-column virtual window (1.5% of the inputs). This deterministic SSR check verifies the initial mount is bounded, but does not profile browser scrolling or client runtime performance.

## Borrowing, Department Reporting, and Voting Workflows

Borrowing states used by the app include `REQUESTED`, `APPROVED`, `REJECTED`, `BORROWED`, `RETURNED`, `OVERDUE`, `LOST`, `DAMAGED`, and `CANCELLED`. The implemented path creates a `REQUESTED` loan and reserves an available copy, exposes that persisted request to the librarian queue, allows librarian approval/rejection, releases the copy on rejection, issues approved requests with a due date, and shows each user their own request/loan status. Student/faculty cancellation is limited to backend-eligible requests. The partial unique index prevents two active requests from claiming one physical copy; workflow changes create supported in-app notifications. Return/renewal and reservations remain incomplete workflows.

Department report filters (`start_date`, `end_date`, `category_id`, `user_type`, `suggestion_status`, `search`) affect database queries; authenticated department identity controls scope. Category options are loaded from the backend. Dashboard values are query-derived, not screenshot constants. Loading, retry/error, empty suggestion, and filter reset behavior exist in the UI. `Print Report` invokes the browser print dialog; unavailable navigation is disabled and labeled. Filter and scope APIs are tested, but browser interaction remains unverified.

Suggestion results include `vote_count` and `voted_by_me`. Voting persists a unique user/suggestion vote and is idempotent on repeated requests; the UI shows voted/loading/error feedback. Vote state is retrieved from the API after reload; vote removal is not supported.

All API successes use `{status:"success",data:...}` and errors use `{status:"error",error:{code,message}}`. Protected endpoints require bearer JWT and enforce role/ownership checks server-side; SQLAlchemy failures are rolled back without exposing internal exception details.

## Development Workflow (Windows PowerShell)
Backend: run `scripts/run_backend.ps1` from repo root. It creates/uses `backend/.venv`, installs requirements, explicitly selects SQLite/testing, seeds idempotently, sets CORS and ephemeral JWT secret, and starts Flask at port 5001.
Frontend: run `scripts/run_frontend.ps1` from repo root. It sets `VITE_API_URL=http://localhost:5001`, `VITE_AUTH_MODE=testing`, installs npm dependencies if absent, and starts Vite on port 5173.
Open `http://127.0.0.1:5173`; health: `http://127.0.0.1:5001/api/health`.
Demo accounts: Urvashi / `25EMCAD016` / STUDENT; Yashdeep / `25TECAD016` / FACULTY; Dhruv / `25DMCAD016` / DEPARTMENT; Sphere / `25LIB016` / LIBRARIAN. These are test accounts, not verified institutional identities. Passwordless test authentication is not identity verification and must remain testing-only.

## Testing and Validation
Backend tests (PowerShell): remove inherited `PYTHONPATH`, then run `backend/.venv/Scripts/python.exe -m unittest discover -s tests -v` from repo root. Frontend production build: `npm run build` in `frontend/`. No frontend lint/test script is defined in `frontend/package.json`.
Verified 2026-10-15: full backend suite **28 tests passed** using the backend venv and SQLite test configuration. `npm run build` passed on Vite 5.4.21 (2311 modules); non-fatal JS bundle warning at 605.07 kB (500 kB advisory). Backend tests cover seeded account counts/mappings/idempotence, auth, SQLite FKs, borrowing, pagination, reports, and vote status. `git diff --check` passed before the final documentation edits and must be rerun. Persistent seeding/live DB integrity inspection was denied by the terminal tool's explicit no-consent gate and was not retried. No browser E2E, live health, or virtualization measurement is claimed. No frontend lint/test script was found.

## Coding and Security Conventions
Preserve React/JavaScript/Vite and Flask/SQLAlchemy. Keep database configuration centralized; testing must explicitly use SQLite. Preserve user data; never reset persistent DB by default. Validate inputs server-side, apply authorization to every protected/state-changing route, use the authenticated DB identity for roles and scope, and roll back failed transactions. Keep secrets out of source/docs. Reuse existing ORM entities and service/API patterns; avoid redundant endpoints and unnecessary dependencies. Keep `Book` distinct from `BookCopy`.

## Reusable Hermes Skills
Fourteen reusable LibSphere-specific skills are available in the active Hermes profile under `skills/libsphere/<skill-name>/SKILL.md` (user-local runtime skill storage, not committed to this repository): `libsphere-fullstack-architecture`, `libsphere-react-vite`, `libsphere-dashboard-ux`, `libsphere-css-motion`, `libsphere-auth-rbac`, `libsphere-sqlalchemy-sqlite`, `libsphere-circulation`, `libsphere-search-pagination`, `libsphere-testing-debugging`, `libsphere-app-security`, `libsphere-notifications-jobs`, `libsphere-analytics-reporting`, `libsphere-operations`, and `libsphere-hermes-project-workflow`. `skills_list(category='libsphere')` verified all 14 are discoverable; use `skill_view(name='<skill>')` to read one. They are procedures, not implementation evidence; the repository `AGENT.md` remains authoritative for current state.

## Current Development Status and Next Steps
Current branch is `main`; the worktree contains existing modifications and untracked files. Preserve all of them. Outstanding: obtain authorization before persistent seeding/integrity checks; run both servers and browser E2E; record actual virtual list mounted count; verify current persistent file state. PostgreSQL remains future scope.

## Task Completion History
- 2026-10-15: Existing LibSphere app updated in place: SQLite local defaults/seed setup; canonical testing login; 141 user and nine department seed; borrowing request/review/issue; student/faculty Requested Books; pagination and visible-row virtualization; persistent vote state; filtered department reports; accurately labeled unavailable navigation; README/AGENT updates. Added tests. Full backend suite passed 28; Vite build passed with 605.07 kB chunk advisory. Persistent DB command was explicitly blocked and not retried; browser E2E and performance profiling remain outstanding. Fourteen reusable LibSphere skills exist in the active user-local Hermes profile, not in the repository.
