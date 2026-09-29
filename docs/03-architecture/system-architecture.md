# System Architecture
**Status:** Planned

```text
┌─────────────────────────────────────┐
│             FRONTEND                │
│      React + JavaScript + Vite      │
└──────────────────┬──────────────────┘
                   │ HTTP / JSON API
                   ▼
┌─────────────────────────────────────┐
│              BACKEND                │
│          FastAPI + Python           │
├─────────────────────────────────────┤
│ API → Services → Repositories       │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│             PostgreSQL              │
└─────────────────────────────────────┘
```

## Principles
- The **frontend never connects directly to PostgreSQL.**
- Backend layers: API/Routes → Services (business logic) → Repositories (data access) → PostgreSQL.
- One common `users` table for all roles.
- **Book ≠ Book copy** is the basis of inventory and borrowing.
- Permissions are centralized; authorization is enforced on the backend.
- Secrets live in `.env`, never in Git.
- No Redis, Elasticsearch or microservices without a demonstrated need.

## Repository boundaries
```text
MITRC-LibSphere
├── docs        → project knowledge and engineering documentation
├── frontend    → React user interface
├── backend     → FastAPI application and business logic
├── database    → PostgreSQL schema, migrations and seed data
├── scripts     → setup / automation / backup
└── tests       → integration and end-to-end verification
```

## Initial project root (first milestone only)
`frontend/ backend/ database/ docs/ scripts/ .env.example .gitignore docker-compose.yml README.md`. Other files are created progressively as features land; do not pre-create hundreds of empty files.

## Full planned tree
See [frontend](frontend-architecture.md) and [backend](backend-architecture.md) architecture for the detailed trees.
