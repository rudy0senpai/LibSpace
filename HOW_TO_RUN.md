# LibSphere — How to Run (Windows PowerShell)

This guide is for the current prototype in this repository. **Normal mode** means local development with normal (email/password) API authentication; it does not mean that this prototype is production-ready. **Local Testing Mode** uses an isolated SQLite demo database and a passwordless demo login. Never enable testing authentication in production.

Run PowerShell commands from the repository root unless a step says otherwise. Use separate PowerShell windows for the backend and frontend. Environment variables set with `$env:...` apply only to that PowerShell process and its children; set them again in the other/new terminal when needed.

## Prerequisites

The repository does not declare a supported Python range or a Node `engines` range. The dependency files do not pin Python package versions. On the Windows environment inspected for this guide, Python **3.14.7**, Node.js **v26.7.0**, and npm **11.19.0** were installed; treat these as observed versions, not an official compatibility promise. The backend test suite and frontend build had been verified in this checkout. If you encounter a runtime-specific package issue, record the exact versions before changing dependencies.

Verify installed tools in PowerShell:

```powershell
py --version
py -0p
node --version
npm.cmd --version
```

Required project dependencies:

- Python packages listed in `backend/requirements.txt`: Flask, Flask-CORS, Flask-SQLAlchemy, Flask-JWT-Extended, python-dotenv, and Werkzeug. SQLite is provided by Python; there is no separate database server requirement for the documented local modes.
- Frontend dependencies declared in `frontend/package.json` (React, Vite, and related packages). `frontend/package-lock.json` may exist in a local checkout but is ignored by Git and is not tracked in the repository.
- Windows PowerShell and the Python `py` launcher are used in the commands below. Node/npm must run as native Windows programs for this PowerShell workflow; do not mix WSL `node_modules` with Windows Node or vice versa.

There is no configured migration framework/command. `backend/app.py` and `backend/init_db.py` use SQLAlchemy `db.create_all()` to create missing tables; this is not a schema migration system and will not migrate existing table structures.

## One-time installation

1. Open PowerShell and change to the repository root:

   ```powershell
   Set-Location 'C:\path\to\LibSpace'
   ```

2. Create the backend virtual environment if it does not exist, then install backend requirements. Repeat the pip install only after dependencies change or if the environment is incomplete:

   ```powershell
   if (-not (Test-Path .\backend\.venv\Scripts\python.exe)) {
       py -3 -m venv .\backend\.venv
   }
   $python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
   & $python -m pip install -r .\backend\requirements.txt
   ```

3. Install the frontend dependencies declared in `frontend/package.json`. The repository ignores the local `package-lock.json`, so `npm install` is the fresh-checkout command; it may create/update an ignored local lockfile:

   ```powershell
   Push-Location .\frontend
   npm.cmd install
   Pop-Location
   ```

   Repeat after dependency changes or if the install is incomplete. Do not delete a local lockfile to troubleshoot.

## Configuration overview

`backend/config.py` loads a root-level `.env` file. The frontend's Vite configuration also reads the repository root for Vite environment files (`envDir: '..'`). The example files are templates; `.env.example` and `.env.testing.example` are **not** automatically loaded by their names.

- `APP_ENV`: backend mode (`development`, `testing`, or `production`). Testing mode rejects a non-SQLite database URL.
- `DATABASE_URL`: SQLAlchemy connection URL. Local development defaults to `sqlite:///libsphere.db`; testing defaults to `sqlite:///libsphere_test.db`. Relative SQLite paths resolve under `backend/instance/` (so the persistent testing file is `backend/instance/libsphere_test.db`).
- `JWT_SECRET_KEY`: signing secret for backend access tokens. Supply a unique random value; do not commit it, paste it into chat, or reuse a production secret for local work. The code also recognizes legacy `JWT_SECRET`, but prefer `JWT_SECRET_KEY`.
- `JWT_ACCESS_TOKEN_HOURS`: token lifetime in hours (default `8`).
- `BACKEND_HOST` / `BACKEND_PORT`: Flask bind address and port (defaults `127.0.0.1` / `5001`).
- `CORS_ORIGINS`: comma-separated exact browser origins allowed to call the API. Scheme, hostname, and port must match the frontend URL.
- `FRONTEND_URL`: local frontend origin used in the default CORS list (`http://localhost:5173`).
- `VITE_API_URL`: API base URL compiled/used by the frontend, normally `http://localhost:5001`.
- `VITE_AUTH_MODE=testing`: shows the passwordless three-field demo login. Do not set this outside local testing.

For a fresh local secret in the current PowerShell session, generate 32 random bytes (the value is never printed):

```powershell
$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$env:JWT_SECRET_KEY = [Convert]::ToBase64String($bytes)
$rng.Dispose()
```

For repeated local use, create a root `.env` only if one is not already present, then edit its values locally (in particular replace the example JWT placeholder with a unique secret):

```powershell
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
notepad .\.env
```

`.env` is ignored by Git in this repository; still confirm `git status` before committing and never put real credentials in documentation. The PowerShell session variables take precedence over values loaded from `.env`.

## Normal Mode — local development (not a production deployment)

The normal backend login endpoint accepts email/password and checks a stored password hash. However, **normal login is not fully connected to the frontend**: when `VITE_AUTH_MODE` is not `testing`, the current React login page displays “Login is available only in explicit local testing mode” and offers no credential fields. No account-registration/password-reset flow was found. Therefore you can run and check the normal-mode API, but do not claim that a user can sign in through the normal-mode frontend. The legacy `backend/seed_db.py` contains bundled sample account credentials and is not a safe account-provisioning workflow; do not use it as a production or routine setup step.

1. One-time: copy `.env.example` to `.env` at the repository root and configure a private `JWT_SECRET_KEY`. Keep local `APP_ENV=development` and a local SQLite URL such as `sqlite:///libsphere.db`. Do not point local commands at a shared/production database. Alternatively, set the same variables in the backend PowerShell session as below; generating a new secret per session invalidates tokens from any previous session.
2. In the first PowerShell window, from the repository root, start the Flask development server:

   ```powershell
   $python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
   Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
   $env:APP_ENV = 'development'
   $env:DATABASE_URL = 'sqlite:///libsphere.db'
   $env:BACKEND_HOST = '127.0.0.1'
   $env:BACKEND_PORT = '5001'
   $env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
   # Run the random-secret snippet above in this same window, or set JWT_SECRET_KEY privately.
   & $python .\backend\app.py
   ```

   The app creates missing tables on startup. It does not seed accounts in normal mode. Database file: `backend/instance/libsphere.db` when using the relative URL above.

3. In a second PowerShell window, from the repository root, start Vite without testing authentication:

   ```powershell
   Set-Location 'C:\path\to\LibSpace'
   $env:VITE_API_URL = 'http://127.0.0.1:5001'
   Remove-Item Env:VITE_AUTH_MODE -ErrorAction SilentlyContinue
   Push-Location .\frontend
   npm.cmd run dev -- --host 127.0.0.1 --port 5173
   ```

4. Open the frontend at **http://127.0.0.1:5173**. The backend listens at **http://127.0.0.1:5001**. Check backend/database health at **http://127.0.0.1:5001/api/health**:

   ```powershell
   Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/health'
   ```

   A successful response is JSON with `status: success`, `message: LibSphere backend is running`, and `database: ok`. This endpoint confirms DB connectivity and required tables; it does not confirm a seeded user or frontend authentication.

The local Flask server is the development server, and Vite's `dev` command is a development server. A deployment needs separately configured production hosting, HTTPS, a secure database, secrets management, and a production frontend build/serving setup. README identifies PostgreSQL as future deployment scope and says PostgreSQL connectivity has not been verified locally. Do not treat the local setup as production-ready.

## Local Testing Mode — SQLite demo data and test-only login

Use only a disposable/local development machine. Testing mode accepts a seeded **name + user ID + role** and does not verify identity or require a password. It must never be enabled in production.

### Legacy test seeder safety gate

The checked-in `database/seed/books_catalog.json` has blank ISBNs and is retained only for isolated in-memory automated fixtures. The file-backed `backend/seed_test_db.py` path will not create or update records from that legacy blank-ISBN catalogue: it returns without row writes when a sufficiently seeded DB already exists and refuses a fresh file-backed DB if fewer than 12 legacy titles are present. The seeder may still call `db.create_all()` and create its index before the guard, but it does not reset or overwrite profiles/history. A fresh persistent test DB needs a separately reviewed ISBN-backed seed source; the 1,000-book academic import creates bibliographic records only and intentionally does not invent physical copies. Do not use `--reset` or the old no-ISBN importer to bypass the guard.

The command below is retained only for an already-populated local test DB and returns without row changes for file-backed databases; use it only when you understand that safety gate:


```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:TEST_DATABASE_URL = 'sqlite:///libsphere_test.db'
& $python .\backend\seed_test_db.py
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
```

The in-memory seeder builds role/circulation fixtures for automated tests. On a file-backed path the legacy blank-ISBN fixture is gated and not upserted; the existing persistent database retains its current users, books, copies, loans, reservations, suggestions, notifications, and audit rows. The explicit `--reset` option still deletes the configured SQLite file plus WAL/SHM sidecars and is unsafe as a workaround; do not use it to bypass the seeding guard. `scripts/run_backend.ps1` invokes the file-backed seeder, which is a no-op for an already populated test database and refuses a fresh one whose catalog source is blank ISBN.

### Start the backend

In the first PowerShell window, from the repository root:

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
$env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$env:JWT_SECRET_KEY = [Convert]::ToBase64String($bytes)
$rng.Dispose()
& $python .\backend\app.py
```

`app.py` runs `db.create_all()` when launched. With an already initialized test DB, this is non-destructive table creation/check behavior; it does not execute the seeder. The health endpoint checks that the database responds and the required tables exist.

### Start the frontend

In a second PowerShell window, from the repository root:

```powershell
$env:VITE_API_URL = 'http://localhost:5001'
$env:VITE_AUTH_MODE = 'testing'
Push-Location .\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173**. The backend/API is **http://127.0.0.1:5001**; health is **http://127.0.0.1:5001/api/health**. The Vite config sets `strictPort: true`, so it fails rather than silently selecting another port.

### Demo profiles and read-only verification

The supported test login fields are exact **Name**, **User ID**, and **Role** (role selector values `STUDENT`, `FACULTY`, `DEPARTMENT`, `LIBRARIAN`). The required seeded profiles are:

| Name | User ID | Role |
|---|---|---|
| Urvashi | `25EMCAD016` | `STUDENT` |
| Yashdeep | `25TECAD016` | `FACULTY` (UI label: Teacher) |
| Dhruv | `25DMCAD016` | `DEPARTMENT` |
| Sphere | `25LIB016` | `LIBRARIAN` |

The seeder also creates a 141-account cohort: 100 students, 30 faculty, 9 department accounts, and 2 librarians, plus a 119-title catalog and 238 copies. These are demo identities, not verified MITRC personnel. The IDs are matched case-insensitively and surrounding whitespace is trimmed.

Verify without changing database contents:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/health'
$loginBody = @{ name = 'Urvashi'; user_id = '25EMCAD016'; role = 'STUDENT' } | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5001/api/auth/login' -ContentType 'application/json' -Body $loginBody
$headers = @{ Authorization = "Bearer $($session.data.access_token)" }
$catalog = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/books/search?q=Clean' -Headers $headers
$catalog.data.items | Select-Object -First 3 title, author, isbn
```

A valid test login returns an access token and user data; the authenticated catalogue request should return a `data.items` list (possibly empty only if seed data is absent). Do not print or share access tokens. A `401` for the listed demo identity usually means the test DB has not been seeded or the name/ID/role do not match.

## Startup scripts

From the repository root:

- `scripts/run_backend.ps1` is a testing-mode launcher. It removes `PYTHONPATH`, creates the venv if missing, installs backend requirements, selects SQLite/testing/CORS/ephemeral JWT settings, and starts Flask without running a seeder. It requires the existing `backend/instance/libsphere_test.db`; a missing file fails closed because the legacy blank-ISBN seed catalog is not a safe fresh persistent source.
- `scripts/run_frontend.ps1` sets `VITE_API_URL=http://localhost:5001`, `VITE_AUTH_MODE=testing`, installs frontend dependencies with `npm install` only if `frontend/node_modules` is missing, and starts Vite at port 5173. This is a testing-mode launcher, not a normal-mode launcher.
- No separate normal-mode backend launcher is provided. Use the manual normal-mode commands above.

Do not launch a script and a manual server for the same service at the same time.

## Librarian catalogue metadata and availability

The librarian **Manage Catalogue** cards have three separate actions: **Edit metadata** updates bibliographic fields, **Manage availability** changes copy availability, and **Manage copies** adds individual identified copies. Metadata and availability changes are saved through the Flask API; cancelling leaves the database unchanged. Availability totals are derived from `BookCopy` and active `Loan` records, not edited as arbitrary counts. A title with no physical copies remains Not available; add an identified copy through Manage copies before enabling availability. Reducing physical copies below committed/borrowed copies is not offered by the availability dialog.

The API endpoints require a bearer token for an active LIBRARIAN or ADMIN account:

| Method and path | Purpose |
|---|---|
| `GET /api/librarian/catalogue?page=&per_page=&q=` | Search/list catalogue records, including clean description and separate `source_metadata`. |
| `PATCH /api/librarian/catalogue/<book_id>` | Update bibliographic metadata through SQLAlchemy. |
| `GET /api/librarian/catalogue/<book_id>/availability` | Read copy-state counts and current availability. |
| `PATCH /api/librarian/catalogue/<book_id>/availability` | Set `{ "available": true|false, "reason": "..." }`; availability changes copy states transactionally. |
| `POST /api/librarian/catalogue/<book_id>/copies` | Add a physical copy with accession number, barcode, rack, and shelf. |

The backend validates a required title (max 300 characters); ISBN-10/13 checksum and uniqueness (a duplicate returns HTTP 409); publication year 1400–2100; edition/language up to 80 characters; HTTP(S) cover URL up to 500 characters; at most 50 author names of up to 180 characters; text description; and programme/department names or codes that exist. Availability reason is optional and capped at 300 characters. The API returns validation failures in `{status:"error",error:{code,message}}`. A request/loan commitment or an ACTIVE reservation blocks withdrawing available copies. `available_copies` comes from AVAILABLE physical-copy rows, can never be negative or exceed total copies, and a zero-copy title cannot be marked available. Temporary unavailable copies are placed in MAINTENANCE and tracked by `BookAvailabilityHold`; restoration only affects those held copies. SQLite changes use a serialized write transaction. Provenance is stored in `BookSourceMetadata`; recognized legacy provenance text is removed from user-facing descriptions by the additive migration/serializer, and a missing description displays `No description available.`

### Additive SQLite migration (only when needed)

`backend/migrate_catalogue_metadata.py` creates only the `book_source_metadata` and `book_availability_holds` tables and separates recognized legacy provenance. It supports file-backed SQLite only, never resets/reseeds the database, and requires a new explicit backup path. Stop Flask first, confirm `DATABASE_URL` identifies the intended local SQLite file, then run from the repository root:

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $env:USERPROFILE "T450\DataSets\LibSphere_isbn_repair\backups\libsphere_before_catalogue_migration_$stamp.db"
& $python .\backend\migrate_catalogue_metadata.py --backup-path $backup
```

The script creates and verifies the backup before schema/data changes, then verifies SQLite integrity and foreign keys after migration. The backup path must not already exist. Keep the printed backup path for recovery. Do not run this against a production/shared database without a separately approved maintenance plan.

Focused catalogue tests (PowerShell from the repository root):

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
& $python -m unittest discover -s tests -p test_sqlite_seed.py -k availability -v
& $python -m unittest discover -s tests -p test_sqlite_seed.py -k librarian_metadata -v
& $python -m unittest discover -s tests -p test_sqlite_seed.py -k catalogue_update_rejects -v
& $python -m unittest discover -s tests -p test_import_academic_textbooks.py -v
```

Run the full backend suite from the repository root and frontend checks from `frontend/`:

```powershell
& $python -m unittest discover -s tests -v
Push-Location .\frontend
node --test
node .\node_modules\vite\bin\vite.js build
node .\scripts\verify-virtual-grid.mjs
Pop-Location
```

The build may emit Vite's existing non-fatal chunk-size advisory; this is separate from build success. Verified 2026-10-20: backend **77 tests passed**, frontend `node --test` **19 passed**, production build passed (2,327 modules; 660.67 kB JS chunk with the advisory), and the virtual-grid check rendered 12/1,000 initial items. Isolated headless Chrome verified metadata and zero-copy availability dialogs at 390, 768, 1366, and 1920 CSS-pixel widths, with visible actions and no horizontal document overflow. Escape/backdrop close, unsaved confirmation, focus wrapping, scroll locking, and invalid ISBN feedback were exercised manually. No browser save was submitted; database persistence and inventory conflict rules were exercised by backend tests.

## Academic textbook catalogue import

The supplied file is `database/LibSphere_Academic_Textbooks_1000.csv`. Use `backend/import_academic_textbooks.py`; it performs ISBN-10/13 checksum and uniqueness checks, then verifies each ISBN against the ISBN-specific Open Library edition record and compares the title and author before a row is eligible. Publisher/year disagreements are counted and the ISBN edition metadata is preferred in the Book fields; original supplied values and provenance, including the supplied cover URL marked unverified, are stored in `BookSourceMetadata`, separate from the user-facing description. A checksum alone never qualifies a row. The importer is idempotent by normalized ISBN, preserves existing records, and does not create `BookCopy` rows because the CSV has no physical-copy identifiers.

Run the preflight first. It is dry-run by default and reports row/ISBN/duplicate/rejection totals before any DB write:

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
$report = Join-Path $env:USERPROFILE 'T450\DataSets\LibSphere_isbn_repair\reports\academic_textbooks_preflight.json'
& $python .\backend\import_academic_textbooks.py --csv .\database\LibSphere_Academic_Textbooks_1000.csv --database-url $env:DATABASE_URL --report $report
```

Review the JSON evidence, then apply with a verified online backup:

```powershell
& $python .\backend\import_academic_textbooks.py --csv .\database\LibSphere_Academic_Textbooks_1000.csv --database-url $env:DATABASE_URL --report $report --apply
```

The report records the CSV SHA-256, per-row matching evidence, backup, import totals, and final protected-table totals. The backup is created under `backend/instance/academic_import_backups` before writes. To safely rerun without provider calls, use `--use-preflight $report --report $report --apply`; the CSV path and SHA-256 must still match. The separate `backend/import_books_csv.py` legacy importer rejects blank/invalid ISBN rows and is not the academic import path. The old 10,000-row generated CSV has no ISBNs and should not be imported.

### Roll back an import

Stop Flask first. Keep the current file as a safety copy, then restore the exact backup path recorded in the import JSON using SQLite's backup API (do not delete DB/WAL/SHM files):

```powershell
$database = (Resolve-Path .\backend\instance\libsphere_test.db).Path
$backup = 'C:\path\to\academic_import_backups\libsphere_test_before_academic_import_TIMESTAMP.db'
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Copy-Item $database "$database.pre-restore"
$restore = @'
import sqlite3, sys
source = sqlite3.connect('file:' + sys.argv[1].replace('\\', '/') + '?mode=ro', uri=True)
target = sqlite3.connect(sys.argv[2])
source.backup(target)
assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not target.execute('PRAGMA foreign_key_check').fetchall()
target.close(); source.close()
'@
& $python -c $restore $backup $database
```

## Cover retrieval, catalogue cards, and UI behavior

`BookCoverCard` uses the authenticated Flask `GET /api/books/<book_id>/cover` endpoint; React never accesses SQLite or provider APIs directly. Cards request covers lazily near the viewport. The public search serializer's `cover_image_ref` field is the image binding. On an image load error, the card makes one bounded backend retry with `?failed=1`; the service excludes the failed URL, checks alternate providers and returns a new verified match if available. The frontend advances through deduplicated candidates once, then displays the existing 2:3 portrait placeholder. It does not loop on a broken URL. The lookup order is ISBN-specific Open Library, Google Books ISBN (exact ISBN identifier plus matching title/author), then verified Google and Open Library title/author search. Publisher/year/edition are compared when supplied; description/subject terms refine search but cannot substitute for identity. Redirected provider responses are accepted only when the response contains a usable image body, not just HTTP 200. The staff-only `?refresh=1` action remains an explicit refresh, and a failed refresh never overwrites a valid stored URL.

Successful and unsuccessful lookups persist in the additive `cover_lookup_cache` table with source, status, attempt time, and expiry; `db.create_all()` creates this table without migrating/rebuilding existing tables. Successful matches are cached for 30 days; failures default to a one-day TTL (`COVERS_FAILED_CACHE_TTL_SECONDS=86400`) and are retried after expiry. Defaults are `COVERS_TIMEOUT_SECONDS=5`, `COVERS_RETRIES=2`, and `COVERS_MIN_REQUEST_INTERVAL=1`. Provider requests use bounded exponential backoff, per-process throttling, and in-flight deduplication. Logs include ISBN, provider outcome/status and retry reason without credentials. The service stores external URLs and source attribution only; it does not permanently download provider images. Follow Open Library/Google Books terms and attribution policies. Structured academic-source provenance remains separate from book descriptions; both the API serializer and card suppress the recognized legacy provenance prefix.

Process missing covers progressively (the command is not called at startup):

```powershell
& $python .\backend\fetch_missing_covers.py --database-url 'sqlite:///libsphere_test.db' --limit 50 --batch-size 10
& $python .\backend\fetch_missing_covers.py --database-url 'sqlite:///libsphere_test.db' --limit 50 --retry-failed
& $python .\backend\fetch_missing_covers.py --database-url 'sqlite:///libsphere_test.db' --refresh-book-id 'BOOK_UUID'
```

The JSON summary includes records processed, matched, unresolved, provider-failed, skipped, deferred candidates, and unresolved ISBNs. Keep batches small; run the command explicitly and verify the target SQLite URL first. On 2026-10-20, a backed-up active-catalogue batch processed 10 candidates: 3 verified covers added, 7 unresolved/provider-failed, 80 skipped, and 992 eligible candidates deferred. The three saved URLs were `openlibrary_title_author` matches and each revalidated as an image response. The catalogue changed from 69 to 72 populated cover references; 1,082 books remained, with no reset/reseed/deletion. Backup: `%USERPROFILE%\T450\DataSets\LibSphere_isbn_repair\backups\libsphere_before_cover_repair_20261020_201035.db` (`integrity_check=ok`, zero FK errors). Google Books returned HTTP 429 for the batch (configured default daily quota is zero); several Open Library ISBN edition lookups returned HTTP 404, so unresolved records remain cached for later retry rather than being labeled permanently unavailable. Unresolved ISBNs in this batch: `9781668452127`, `9783110659344`, `9780262082136`, `9798369347614`, `9783031126406`, `9781119694960`, `9789811509803`. This was a bounded batch, not a full-catalogue repair.

Catalogue cover frames reserve a portrait 2:3 ratio and use `object-fit: contain`, lazy loading, and a local placeholder. Shared primary-action colors are `--dashboard-button-bg`, `--dashboard-button-hover`, `--dashboard-button-active`, and `--dashboard-button-ink`; both dark/night and light themes keep button labels at or above 4.5:1 contrast. Focus remains visible, disabled states remain legible, and Request Book is warm amber with dark text. The Notifications sidebar entry is removed for Student, Faculty, Department, and Librarian; the separate header notification feed and backend notification APIs/data remain intact.

### Verified 2026-10-19 dataset import

Preflight checked 1,000 source rows: all 1,000 ISBN checksums valid and unique; Open Library returned edition data for all 1,000; 963 title/author associations passed and 37 were rejected for mismatch. Source publisher disagreed with edition evidence on 206 accepted rows and source publication year on 286; source values are retained in provenance notes, while ISBN-edition publisher/year are used in supported Book fields when available. The 963 accepted records were created, 0 physical copies were created, and rerunning the exact saved preflight created 0 additional books (963 matched). Active test DB after import: 1,082 books, 1,026 ISBN-bearing with no invalid/duplicate normalized ISBNs, 56 blank ISBN books retained, 238 copies, 18 loans, 3 reservations, 141 users, 13 suggestions, 25 votes, 31 notifications. Existing `cover_image_ref` values remain; CSV cover URLs are recorded as unverified provenance and are not served as trusted covers. Backup: `backend/instance/academic_import_backups/libsphere_test_before_academic_import_20261019_174148.db` (`integrity_check=ok`, zero FK errors). The JSON preflight/import report is under `%USERPROFILE%\T450\DataSets\LibSphere_isbn_repair\reports\academic_textbooks_preflight_latest.json`.

The 56 retained blank-ISBN records have dependent copies/history and were not deleted. The legacy `books_catalog.json` still has blank-ISBN fixture entries: in-memory automated tests use those demo fixtures, but file-backed seeding refuses a fresh database with fewer than 12 existing legacy titles and returns without upserting the blank-ISBN fixture when the existing file DB is present. Thus a fresh persistent testing DB needs a separately reviewed ISBN-backed seed source; do not use `--reset` or the retired 10,000-row CSV to bypass this gate.

### Verification and remaining limits

Verified in this checkout: backend `unittest discover` **70 passed**; frontend `node --test` **16 passed**; Vite production build succeeded (2,326 modules; existing >500 kB chunk warning); virtual-grid smoke rendered **12/1,000** initial items. The live Flask health route returned HTTP 200, and an authenticated ISBN cover lookup returned Open Library with a persisted cache hit on repeat. SQLite `integrity_check` was `ok`, foreign-key check had 0 errors, and `git diff --check` passed. PowerShell syntax parsing passed for 19 documented blocks plus `scripts/run_backend.ps1`. No bulk cover batch or browser screenshot/overflow inspection was run after these edits; no lint script is configured. The 37 rejected source records and 56 pre-existing blank-ISBN records remain explicit limitations.

## ISBN repair — verified, dry-run first

`backend/repair_book_isbns.py` targets an existing file-backed SQLite DB only and refuses to create a missing database. For the active local test app, the verified target is `backend/instance/libsphere_test.db` from `sqlite:///libsphere_test.db`. Before the first write, a separate SQLite online-backup snapshot and baseline/export were created and verified; the repair CLI is dry-run-first and its research mode reads the DB read-only while writing reports and cache files. `--apply-report` creates another fresh verified backup, revalidates source evidence and current book fields inside a transaction, applies only `VERIFIED` ISBNs, fills only missing cover references after a successful image response, and writes a timestamped audit. It never changes authors/titles, copy/loan/reservation rows, or curated cover references. No unresolved record was removed during the run.

Run from the repository root in PowerShell; first ensure the backend is using the intended test database, never a production/shared file:

```powershell
$python = (Resolve-Path .\\backend\\.venv\\Scripts\\python.exe).Path
$repairOutput = Join-Path $env:USERPROFILE 'T450\\DataSets\\LibSphere_isbn_repair'
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
& $python .\\backend\\repair_book_isbns.py --database-url 'sqlite:///libsphere_test.db' --out-dir $repairOutput --limit 119 --check-covers
```

The command above researches the curated source-keyed subset. To search unmapped books by title/author, add `--research-unmapped`; use `--limit N` to bound a batch and rerun later. Successful provider responses are cached in `$repairOutput\\cache`; the script respects Open Library's 1-second minimum gap and stops after HTTP 429 rather than retrying aggressively. Google Books returned HTTP 429 during this run, so that provider was not available. Provider errors, no results from an incomplete query, and ambiguous editions stay `REVIEW_REQUIRED`, not `NOT_FOUND`. The current app has 10,000 generated/unverified catalogue rows without Open Library work keys, so broad research remains incomplete; do not treat the initial 10-record query batch as catalogue-wide research.

Review the CSV and JSON paths printed by the dry run. Apply only after checking the `VERIFIED` rows and using the exact report path:

```powershell
$report = Join-Path $repairOutput 'reports\\isbn_repair_dry_run_TIMESTAMP.csv'
& $python .\\backend\\repair_book_isbns.py --database-url 'sqlite:///libsphere_test.db' --out-dir $repairOutput --apply-report $report
```

Do not pass `--delete-not-found` unless a separate human-reviewed report establishes `NOT_FOUND` with complete searches and every retained relation is safe to remove. The current script/run produced no `NOT_FOUND` rows and removed no books. Rerunning an applied report is idempotent: existing valid ISBNs are skipped.

### 2026-10-18 repair result and artifacts

Baseline backup: `$repairOutput\\backups\\libsphere_test_before_isbn_repair_20261018_152811.db` (`integrity_check=ok`, zero foreign-key errors, SHA-256 `ba09fbd284b3766208799e0e7ffbc1634cc5cb1f37c5873262df3e47e23d8972`). Baseline: 10,119 books (all ISBNs missing), 238 copies, 18 loans (12 active), 3 reservations (2 active), 13 suggestions, 25 votes, 31 notifications, 141 users, 10,187 book-author links, and 6,211 book-department links. The initial missing/invalid export is `reports\\books_missing_or_invalid_isbn_20261018_152811.csv`; baseline JSON is `reports\\isbn_repair_baseline_20261018_152811.json`.

The reviewed dry run is `reports\\isbn_repair_dry_run_20261018_155907.csv` (JSON summary alongside it). It contained 63 unique checksum-valid ISBNs matched to exact Open Library work/edition/title/author/year/publisher evidence and 10,056 `REVIEW_REQUIRED` books. A separate 10-record unmapped title/author sample stayed review-only; Google Books returned 429. Applied backup: `$repairOutput\\backups\\libsphere_test_before_isbn_apply_20261018_155940.db` (integrity ok, zero FK errors, same SHA-256 because the catalogue had not changed since baseline). Audit CSV: `reports\\isbn_repair_audit_20261018_155940.csv` (old/new ISBN, source/evidence, action, and timestamp).

After application: 63 ISBNs added and 56 verified image cover URLs stored; 10,119 books remain, of which 10,056 lack ISBN; invalid ISBNs 0, duplicate normalized ISBNs 0, removals 0. Copies (238), loans (18 / 12 active), reservations (3 / 2 active), and all related user/history tables were unchanged. SQLite `integrity_check` returned `ok`; `foreign_key_check` returned zero rows. ISBN repair is partial: do not claim all catalogue books have ISBNs.

### Restore the pre-apply backup safely

Stop the Flask backend before restoring. This creates a separate SQLite-online-backup copy of the current file first, then restores the timestamped backup using SQLite's backup API (do not delete DB/WAL/SHM files):

```powershell
$python = (Resolve-Path .\\backend\\.venv\\Scripts\\python.exe).Path
$repairOutput = Join-Path $env:USERPROFILE 'T450\\DataSets\\LibSphere_isbn_repair'
$database = (Resolve-Path .\\backend\\instance\\libsphere_test.db).Path
$backup = Join-Path $repairOutput 'backups\\libsphere_test_before_isbn_apply_20261018_155940.db'
$safetyCopy = "$database.pre-restore.db"
$restore = @'
import pathlib, sqlite3, sys
database, backup, safety_copy = sys.argv[1:]
current = sqlite3.connect(database)
safety = sqlite3.connect(safety_copy)
current.backup(safety)
safety.close(); current.close()
source = sqlite3.connect("file:" + pathlib.Path(backup).as_posix() + "?mode=ro", uri=True)
target = sqlite3.connect(database)
source.backup(target)
assert target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
assert not target.execute("PRAGMA foreign_key_check").fetchall()
target.close(); source.close()
'@
& $python -c $restore $database $backup $safetyCopy
```

## Troubleshooting

### Backend port 5001 is already in use

Identify the listener before changing or stopping anything:

```powershell
$listeners = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
$listeners | Select-Object LocalAddress, LocalPort, OwningProcess
$listeners | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path }
```

If the process is a LibSphere backend you started in another terminal, stop it there with `Ctrl+C`. Do not kill an unidentified process. Alternatively choose another backend port, update `BACKEND_PORT`, `VITE_API_URL`, and the frontend CORS origin as appropriate, then restart both services. Update health-check URLs too.

### Frontend port 5173 is already in use

Use the same listener-inspection commands with `-LocalPort 5173`; identify the owning process before acting. The current Vite config uses `strictPort`, and the launcher requests port 5173, so startup will fail instead of silently moving. Stop only a confirmed LibSphere frontend that you own, or intentionally select another Vite port and add that exact origin to backend `CORS_ORIGINS` before restarting the backend.

### Python environment or dependency errors

From the repository root, check `py -0p`, `& $python --version`, and `& $python -m pip --version`. Ensure `$python` points to `backend\.venv\Scripts\python.exe`, not another Python installation. Recreate the venv only if it is corrupt (this removes only the virtual environment, not the database):

```powershell
Remove-Item -Recurse -Force .\backend\.venv
py -3 -m venv .\backend\.venv
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
& $python -m pip install -r .\backend\requirements.txt
```

Do not run removal if the path is not exactly the project virtual environment. If your Python version is unsupported by one of the dependencies, use an installed version verified against the current package requirements; the repository itself does not publish an official version range.

### Node.js/npm runtime mismatch or Windows versus WSL

Check `node --version`, `npm.cmd --version`, `Get-Command node`, and `Get-Command npm`. Run PowerShell commands in native Windows PowerShell with Windows Node/npm. Do not share `node_modules` between WSL and Windows; install dependencies in the same environment that runs Vite. The repo does not declare a supported Node range, so the installed version alone is not proof of compatibility.

### Missing Rollup native optional dependency

Check the platform/architecture with `node -p "process.platform + ' ' + process.arch"` and verify that Node/npm are native Windows, not WSL. From `frontend`, restore dependencies from `package.json` with:

```powershell
npm.cmd install
```

If it persists, record the full error plus `node --version`, `npm.cmd --version`, and `node -p "process.platform + ' ' + process.arch"`; do not delete the lockfile or manually add arbitrary platform packages.

### CORS errors

Compare the browser's exact origin (including `http`/`https`, hostname, and port) to `CORS_ORIGINS`. The default local allowed origins are `http://localhost:5173` and `http://127.0.0.1:5173`. Ensure `VITE_API_URL` targets the running backend and restart Flask after changing its CORS environment variable. Restart Vite after changing `VITE_API_URL` or `VITE_AUTH_MODE` because Vite reads those variables at start/build time.

### Backend health-check fails

Check that Flask is listening on port 5001 and request `http://127.0.0.1:5001/api/health` with `Invoke-RestMethod`. A `503` means the backend is running but cannot reach its database or required tables are missing; read the backend terminal traceback and verify `APP_ENV` and `DATABASE_URL`. Testing mode requires a SQLite URL. Relative SQLite URLs resolve under `backend/instance`. Do not delete a database to clear a health error.

### Database connection or missing demo accounts

Check the backend terminal error, `APP_ENV`, and `DATABASE_URL`; testing mode refuses non-SQLite URLs. Confirm the configured test file is `backend/instance/libsphere_test.db`. The health endpoint checks schema/connectivity only, not account counts. If no test profile can log in, confirm the test seed is present before deciding to seed; run the optional seed command only if you accept its documented writes. Never use `--reset` as a first troubleshooting step.

### Authentication or role-routing failures

In testing mode, ensure both processes use testing mode: backend `APP_ENV=testing` and frontend `VITE_AUTH_MODE=testing`. Use a listed demo name, ID, and matching role; all three must identify the same seeded account. Role routes use the role returned by the backend, not a role-only UI choice. In normal mode, the backend login API expects email/password but the current frontend deliberately shows no credential form; passwordless demo login works only when both testing-mode gates are enabled. Do not enable those gates in production.

If the three-field form displays **“Email and password are required.”**, do not change the frontend payload or weaken authentication. That is the backend's normal-auth `MISSING_CREDENTIALS` response: the Vite process is using `VITE_AUTH_MODE=testing`, but the Flask process is not using `APP_ENV=testing`. Stop only the confirmed LibSphere backend process, then restart it from the repository root with the testing SQLite URL and without running the seeder:

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
$env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
# Generate/set JWT_SECRET_KEY in this same PowerShell session using the snippet above.
& $python .\backend\app.py
```

Keep the Vite process at `VITE_AUTH_MODE=testing`; restart it if that environment value was changed. A genuinely mismatched name/ID/role in a testing backend returns HTTP 401 `INVALID_IDENTITY` with “Name, user ID, and role did not match an active local testing account.”

## Stop and restart

Stop each service in its own PowerShell window with **Ctrl+C**. If PowerShell was started in a pushed directory, `Pop-Location` returns to the previous directory; otherwise close that terminal after stopping the server. To restart, rerun only the backend command in the backend terminal and the frontend command in the frontend terminal, restoring the required session environment variables first. If a port is reported busy, identify the listener and process as described above; do not kill unrelated processes.