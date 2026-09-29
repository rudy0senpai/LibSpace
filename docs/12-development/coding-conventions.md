# Coding Conventions and Engineering Rules
**Status:** Planned

Act as a senior full-stack engineer. Before a major feature: inspect the existing project; understand what works; identify affected frontend/backend/database modules; avoid unnecessary rewrites; preserve working functionality; follow the directory structure; keep layer boundaries clean; enforce authorization on the backend; reuse components/services; add tests; update docs; prefer incremental changes.

Do not: introduce frameworks without reason; replace JavaScript with TypeScript; replace FastAPI/PostgreSQL without approval; add unnecessary microservices; over-engineer the MVP.

## Feature workflow
```text
Requirement → Inspect architecture → Identify affected layers → Update schema if required
→ Implement backend → Implement frontend → Add validation/security → Add tests → Update docs → Verify integration
```
## Database change rule
`Model → Migration → Schema → Repository → Service → API → Frontend`. No silent destructive changes.

## Stack notes
Frontend: JavaScript, `.jsx`, Tailwind. Backend: layered FastAPI. Use structured errors, pagination, ORM/parameterized queries, centralized permissions.
