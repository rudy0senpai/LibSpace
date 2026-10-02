# LibSphere — Database + Department Dashboard Implementation

This package adds a PostgreSQL source of truth, realistic demo data, FastAPI analytics API, and a React/JavaScript department dashboard.

## 1. Start PostgreSQL

Recommended:

```bash
docker compose up -d postgres
```

Or use an existing PostgreSQL 14+ server and set `DATABASE_URL`.

## 2. Initialize manually

```bash
psql "$DATABASE_URL" -f database/schema/schema.sql
psql "$DATABASE_URL" -f database/seed/seed.sql
```

The seed contains fictional MITRC users and real published book metadata. Demo password for all seeded users: `LibSphere@2026`.

Department dashboard demo account:
`priya.sharma@mitrc.ac.in`

## 3. Start API

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 4. Start dashboard

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The dashboard calls `GET /api/reports/department/dashboard` and all cards/charts/table values originate from PostgreSQL through FastAPI.

## 5. Data flow

React → FastAPI → Repository SQL → PostgreSQL

The browser never connects directly to PostgreSQL.

## 6. Important

The screenshot values are not seeded as dashboard constants. The UI renders the values returned by PostgreSQL.
