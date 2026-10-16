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

### Optional first-time seed (writes the testing database)

The persistent test database path is `backend/instance/libsphere_test.db`; with the relative SQLAlchemy URL its setting is `sqlite:///libsphere_test.db`. The seeder creates tables and inserts/updates demo records. It is repeatable and does not reset/delete existing data by default, but it **does write/update rows**. Do not run it if you need a strictly read-only start. It rejects non-SQLite URLs and limits the selected database file to `backend/instance/`.

Only if the testing database is new or missing its seeded demo data, and you intend to write the local test DB, run once from the repository root:

```powershell
$python = (Resolve-Path .\backend\.venv\Scripts\python.exe).Path
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:TEST_DATABASE_URL = 'sqlite:///libsphere_test.db'
& $python .\backend\seed_test_db.py
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
```

The seeder creates the schema and adds/upserts the testing cohort, catalog, copies, sample workflow records, notifications, and audit events. The explicit `--reset` option deletes the configured SQLite file plus its WAL/SHM sidecars before seeding; **do not use `--reset` for routine setup**. Do not run the legacy `backend/seed_db.py` for this mode. The startup script `scripts/run_backend.ps1` invokes the testing seeder each time it is run (and runs pip install each time); it does not pass `--reset`, but it may upsert demo data. If you want to avoid database writes after initial seeding, use the manual backend startup below instead.

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

- `scripts/run_backend.ps1` is a **testing-mode** launcher. It removes `PYTHONPATH`, creates the venv if missing, runs pip install, sets testing/SQLite/CORS/ephemeral JWT settings, calls `backend/seed_test_db.py`, then starts Flask. Because it seeds on every launch, prefer the manual backend command above for data-preserving daily restarts. It does not use `--reset`.
- `scripts/run_frontend.ps1` sets `VITE_API_URL=http://localhost:5001`, `VITE_AUTH_MODE=testing`, installs frontend dependencies with `npm install` only if `frontend/node_modules` is missing, and starts Vite at port 5173. This is a testing-mode launcher, not a normal-mode launcher.
- No separate normal-mode backend launcher is provided. Use the manual normal-mode commands above.

Do not launch a script and a manual server for the same service at the same time.

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

## Stop and restart

Stop each service in its own PowerShell window with **Ctrl+C**. If PowerShell was started in a pushed directory, `Pop-Location` returns to the previous directory; otherwise close that terminal after stopping the server. To restart, rerun only the backend command in the backend terminal and the frontend command in the frontend terminal, restoring the required session environment variables first. If a port is reported busy, identify the listener and process as described above; do not kill unrelated processes.