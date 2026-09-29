# MITRC LibSphere

**Discover • Borrow • Suggest • Learn**

A Library Management & Discovery Portal for the Modern Institute of Technology and Research Centre (MITRC), Alwar, Rajasthan. Built as a college internal hackathon project.

> **Status: Design/documentation stage.** No application code exists yet. Everything below describes the *planned* system. See [docs/README.md](docs/README.md) for the full documentation index and status of each document.

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
| Backend | FastAPI, Python |
| Database | PostgreSQL |
| Containers | Docker Compose (planned; must not delay core work) |

## 7. Architecture
```text
React (HTTP/JSON) → FastAPI: API → Services → Repositories → PostgreSQL
```
The frontend never connects directly to PostgreSQL. See [system architecture](docs/03-architecture/system-architecture.md).

## 8. Planned Directory Structure
```text
MITRC-LibSphere/
├── docs/        project knowledge and engineering documentation
├── frontend/    React user interface
├── backend/     FastAPI application and business logic
├── database/    PostgreSQL schema, migrations and seed data
├── scripts/     setup / automation / backup
└── tests/       integration and end-to-end verification
```
Only these directories plus `.env.example`, `.gitignore`, `docker-compose.yml` and `README.md` belong in the first milestone; everything else is created progressively.

## 9–12. Installation, Environment, Database, Running
*Planned — to be written once the foundation (Phase 1) exists.* See [local development](docs/11-deployment/local-development.md) and [environment variables](docs/11-deployment/environment-variables.md) for the intended setup.

## 13. Testing
See [testing strategy](docs/10-testing/testing-strategy.md).

## 14. Demo
See [end-to-end demo flow](docs/09-workflows/end-to-end-demo-flow.md).

## 15. Contribution
See [git workflow](docs/12-development/git-workflow.md) and [commit conventions](docs/12-development/commit-conventions.md).

## 16. License
*To be decided.* (`LICENSE` file not yet created.)

## 17. Future Scope
See [future scope](docs/15-project-management/future-scope.md).
