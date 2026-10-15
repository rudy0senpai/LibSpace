# LibSphere Project Guide

**Status:** Prototype implementation in progress. Updated 2026-10-16. This guide distinguishes automated SQLite test evidence from persistent-file/browser verification.

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

Inspected routes in `backend/app.py`: `GET /api/health`; `POST /api/auth/login`; `GET /api/auth/me`; `GET /api/books/search`; `GET /api/categories`; `GET /api/reports/department/dashboard`; `GET /api/reports/librarian/dashboard`; `GET /api/librarian/users`; `GET /api/users/me/loans`; `POST /api/users/me/loans/requests`; `GET /api/librarian/loan-requests`; `POST /api/librarian/loan-requests/<loan_id>/review`; `POST /api/librarian/loan-requests/<loan_id>/issue`; `POST /api/users/me/loans/<loan_id>/cancel`; `GET /api/users/me/suggestions`; `POST /api/suggestions`; and `POST /api/suggestions/<suggestion_id>/vote`. Login accepts `{name,user_id,role}` only in testing mode and returns JWT/user data. Protected APIs authorize from the database-backed authenticated account. No logout route was found. Reservation, return, fine payment, audit browsing, and notification-center workflows are not complete API/UI features.

## Roles and Permissions
Enum values: `STUDENT`, `FACULTY`, `DEPARTMENT`, `LIBRARIAN`, `ADMIN`. Department dashboard route permits department, librarian, and admin, and scopes a department user to its associated department. Librarian summary route is LIBRARIAN-only. `GET /api/librarian/users` authorizes active LIBRARIAN or ADMIN identities from the bearer token/database; client query roles only filter results and never grant access. Other permissions must be checked at each endpoint; do not infer them from UI navigation.

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
Seeder creates schema in persistent `backend/instance`, rejects non-SQLite URLs, and is repeatable without resetting data; `--reset` explicitly deletes only the selected test SQLite file and WAL/SHM sidecars. Automated tests verify exactly 100 STUDENT, 30 FACULTY, 9 DEPARTMENT and 2 LIBRARIAN accounts (141 total), all requested departments, canonical user-ID uniqueness, and at least 100 distinct titles (catalog has 119). Read-only inspection of `backend/instance/libsphere_test.db` on 2026-10-16 confirmed those seeded role counts and that all 141 records have `is_active=1`; CSE has 12 enabled STUDENT and 5 enabled FACULTY. No persistent database writes or reseeding were performed during that inspection.

Department account map: B.Tech - CSE=`25DMCAD016` (Dhruv), B.Tech - AI&DS=`DEPT-AIDS`, B.Tech - AI&ML=`DEPT-AIML`, B.Tech - Mechanical=`DEPT-MECH`, B.Tech - Electrical=`DEPT-ELEC`, B.Tech - Civil=`DEPT-CIVIL`, BBA=`DEPT-BBA`, BCA=`DEPT-BCA`, M.Tech=`DEPT-MTECH`. Existing ECE/MBA department rows are retained to preserve relationships. Required demo identities: Urvashi/`25EMCAD016`/STUDENT; Yashdeep/`25TECAD016`/FACULTY; Dhruv/`25DMCAD016`/DEPARTMENT; Sphere/`25LIB016`/LIBRARIAN. All are testing identities, not verified MITRC personnel.

## Features: Verified vs Incomplete
- Implemented and covered by backend tests: case-insensitive local test login with trim-only canonicalization (`TEACHER` aliases `FACULTY`); exact 141-account/nine-department seed; database-backed borrowing request/librarian review/issue and user-scoped loans; server-paginated catalogue search; filtered/scoped department reports; idempotent suggestion voting with current-user state; authorized paginated librarian user listing with sanitized fields and database-derived totals.
- Frontend implements Requested Books for student/faculty dashboards, a librarian request queue and database-backed Users table (search, role/department/status filters, sorting, pagination, loading/empty/error/retry states), visible-row book virtualization, vote feedback, and department report filters/calendar.
- Department Dashboard, Suggestions, and Reports navigation controls now scroll to implemented sections. Book Search, Notifications, Profile, and the unused mobile-menu control remain explicitly disabled/labeled unavailable; `Print Report` opens the browser print dialog. Reservation, return/renewal, fine payment, notification-center, audit browsing, and report export remain incomplete workflows.
- Manual browser verification against the persistent test SQLite DB confirmed department/user pages, date selection and report refresh, nav destinations, user filters/sorting/pagination/empty results, and 141 enabled accounts. Browser verification is limited to the local test DB and demo identities; it is not production authentication testing.

## Borrowing, Department Reporting, and Voting Workflows

Borrowing states used by the app include `REQUESTED`, `APPROVED`, `REJECTED`, `BORROWED`, `RETURNED`, `OVERDUE`, `LOST`, `DAMAGED`, and `CANCELLED`. The implemented path creates a `REQUESTED` loan and reserves an available copy, exposes that persisted request to the librarian queue, allows librarian approval/rejection, releases the copy on rejection, issues approved requests with a due date, and shows each user their own request/loan status. Student/faculty cancellation is limited to backend-eligible requests. The partial unique index prevents two active requests from claiming one physical copy; workflow changes create supported in-app notifications. Return/renewal and reservations remain incomplete workflows.

Department report filters (`start_date`, `end_date`, `category_id`, `user_type`, `suggestion_status`, `search`) affect database queries; authenticated department identity controls scope. The React date picker supports month/year selection, locale display, clearing, and range bounds; backend report dates accept a single inclusive day and use `issued_at >= start` with `issued_at < midnight after end`. Active student/faculty metrics use `User.is_active` and the authenticated department’s `department_id`, not online sessions or borrowing activity; the optional `user_type` filter narrows those counts. Thus the persistent CSE data correctly yields 12 enabled students/5 enabled faculty while global account totals are 100/30. `GET /api/librarian/users` returns authorized database records with name, user ID, role, department, account status, paginated/sorted/filterable results and grouped role totals; it does not return email, password hash, account UUID, or creation timestamp. Category options are loaded from the backend. Dashboard values are query-derived, not screenshot constants. Loading, retry/error, empty suggestion, and filter reset behavior exist in the UI. `Print Report` invokes the browser print dialog. Search, role, department, pagination, authorization and date/scope behavior are covered by API tests; status filtering and browser interaction were also manually verified against the persistent test SQLite database.

Suggestion results include `vote_count` and `voted_by_me`. Voting persists a unique user/suggestion vote and is idempotent on repeated requests; the UI shows voted/loading/error feedback. Vote state is retrieved from the API after reload; vote removal is not supported.

All API successes use `{status:"success",data:...}` and errors use `{status:"error",error:{code,message}}`. Protected endpoints require bearer JWT and enforce role/ownership checks server-side; SQLAlchemy failures are rolled back without exposing internal exception details.

## Development Workflow (Windows PowerShell)
Backend: run `scripts/run_backend.ps1` from repo root. It creates/uses `backend/.venv`, installs requirements, explicitly selects SQLite/testing, seeds idempotently, sets CORS and ephemeral JWT secret, and starts Flask at port 5001.
Frontend: run `scripts/run_frontend.ps1` from repo root. It sets `VITE_API_URL=http://localhost:5001`, `VITE_AUTH_MODE=testing`, installs npm dependencies if absent, and starts Vite on port 5173.
Open `http://127.0.0.1:5173`; health: `http://127.0.0.1:5001/api/health`.
Demo accounts: Urvashi / `25EMCAD016` / STUDENT; Yashdeep / `25TECAD016` / FACULTY; Dhruv / `25DMCAD016` / DEPARTMENT; Sphere / `25LIB016` / LIBRARIAN. These are test accounts, not verified institutional identities. Passwordless test authentication is not identity verification and must remain testing-only.

## Testing and Validation
Backend tests (bash in repo root): `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m unittest discover -s tests -v`. Frontend production build: `npm run build` in `frontend/`; `npm run verify:virtual-grid` runs the deterministic SSR window check. No frontend lint or interaction-test script is defined in `frontend/package.json`.
Verified 2026-10-16: full backend suite **31 tests passed** using the isolated SQLite test configuration (`sqlite://`); Vite production build passed after 2313 modules transformed (616.40 kB JS chunk; non-fatal 500 kB advisory); virtual-grid check rendered 15/1000 items (1.5%) in initial SSR window. The persistent `libsphere_test.db` was read-only queried for role/status counts and used for local browser verification: dashboard/user APIs returned successfully; date report queries included selected end dates; librarian search, role/department/status filters, sorting, pagination, empty state and safe fields rendered. `git diff --check` passed after the final code/documentation edits. Browser checks are manual, not an automated frontend test suite; no lint script exists. No browser production/authenticated deployment check or online-session metric is claimed.

## Coding and Security Conventions
Preserve React/JavaScript/Vite and Flask/SQLAlchemy. Keep database configuration centralized; testing must explicitly use SQLite. Preserve user data; never reset persistent DB by default. Validate inputs server-side, apply authorization to every protected/state-changing route, use the authenticated DB identity for roles and scope, and roll back failed transactions. Keep secrets out of source/docs. Reuse existing ORM entities and service/API patterns; avoid redundant endpoints and unnecessary dependencies. Keep `Book` distinct from `BookCopy`.

## Reusable Hermes Skills
Fourteen reusable LibSphere-specific skills are available in the active Hermes profile under `skills/libsphere/<skill-name>/SKILL.md` (user-local runtime skill storage, not committed to this repository): `libsphere-fullstack-architecture`, `libsphere-react-vite`, `libsphere-dashboard-ux`, `libsphere-css-motion`, `libsphere-auth-rbac`, `libsphere-sqlalchemy-sqlite`, `libsphere-circulation`, `libsphere-search-pagination`, `libsphere-testing-debugging`, `libsphere-app-security`, `libsphere-notifications-jobs`, `libsphere-analytics-reporting`, `libsphere-operations`, and `libsphere-hermes-project-workflow`. `skills_list(category='libsphere')` verified all 14 are discoverable; use `skill_view(name='<skill>')` to read one. They are procedures, not implementation evidence; the repository `AGENT.md` remains authoritative for current state.

## Current Development Status and Next Steps
Current branch is `main`; preserve the modified files in the worktree. Outstanding: frontend automated unit/accessibility tests and linting are not configured; existing return/renewal, fine payment, notification center, report export, and reservation workflows remain incomplete. The task-level local browser checks and read-only persistent test DB counts were completed; PostgreSQL and production authentication remain future scope.

## Task Completion History
- 2026-10-15: Existing LibSphere app updated in place: SQLite local defaults/seed setup; canonical testing login; 141 user and nine department seed; borrowing request/review/issue; student/faculty Requested Books; pagination and visible-row virtualization; persistent vote state; filtered department reports; README/AGENT updates. Backend suite then passed 28; Vite build passed with 605.07 kB chunk advisory. A persistent write/seed command was explicitly blocked and not retried; a separate read-only count query and local browser verification were later completed on 2026-10-16. Fourteen reusable LibSphere skills exist in the active user-local Hermes profile, not in the repository.
- 2026-10-16: Fixed department nav destinations and explicitly unavailable controls; added accessible no-dependency report calendar with inclusive date filtering; added librarian-only/admin-authorized `GET /api/librarian/users`, sanitized DB-backed table, filters/sorting/pagination/states; clarified enabled-account counts as department-scoped. Read-only persistent test DB counts: 100 students and 30 faculty enabled globally (141 accounts total); CSE has 12 students and 5 faculty enabled. Added date/user API regressions. Full backend suite passed 31, frontend build passed with 616.40 kB advisory, virtual-grid SSR check passed; local browser verified department page, calendar range/API refresh, navigation, user filters/sort/pages/empty-state. Production authentication and automated frontend tests/lint remain unverified/unconfigured.
