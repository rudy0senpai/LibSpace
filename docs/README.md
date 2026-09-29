# MITRC LibSphere — Documentation Index

This is the master documentation set for MITRC LibSphere. It is derived from the *Project Context* and the *Complete Documentation & Directory Structure* blueprint.

## Status legend
`Planned` · `In Progress` · `Implemented` · `Tested` · `Deprecated`

**Rule:** never document an unimplemented feature as implemented. Right now the whole system is **Planned**; only the concept and design are done.

## Sections
| # | Section | Contents | Written now |
|---|---|---|---|
| 01 | [Project](01-project/project-overview.md) | Overview, objectives, scope, stakeholders, assumptions, glossary, roadmap | Yes |
| 02 | [Requirements](02-requirements/software-requirements-specification.md) | SRS, functional/non-functional, user stories, business rules, acceptance criteria | Yes |
| 03 | [Architecture](03-architecture/system-architecture.md) | System, frontend, backend, security, data flow, ADRs | Yes |
| 04 | [Design](04-design/er-diagram.md) | Context, sequence, state and ER diagrams (conceptual) | Yes |
| 05 | [Database](05-database/database-overview.md) | Entities, relationships, statuses, migrations, seed data | Yes |
| 06 | [API](06-api/api-overview.md) | Planned REST contract, error codes | Yes |
| 07 | [Security](07-security/security-overview.md) | Auth, RBAC, audit, secrets, checklist | Yes |
| 08 | [Features](08-features/book-catalogue.md) | One doc per feature | Yes |
| 09 | [Workflows](09-workflows/end-to-end-demo-flow.md) | Borrow, return, reservation, suggestion, demo | Yes |
| 10 | [Testing](10-testing/testing-strategy.md) | Strategy and test cases | Yes |
| 11 | [Deployment](11-deployment/local-development.md) | Local setup, env vars, Docker | Yes |
| 12 | [Development](12-development/git-workflow.md) | Conventions, Git, branches, commits | Yes |
| 13 | Operations | Monitoring, logging, backup, incidents | Not yet |
| 14 | [UI/UX](14-ui-ux/design-system.md) | Design direction and screen inventory | Yes |
| 15 | [Project management](15-project-management/development-phases.md) | Phases, priorities, demo plan, checklist, future scope | Yes |

## Not yet written (from the blueprint)
Use cases, requirements traceability matrix, application/integration architecture, component/activity/deployment diagrams, table documentation, indexes, constraints, backup and restore, per-role frontend/backend deployment, rollback, all of section 13, layout/accessibility/responsive/navigation docs, milestone plan. These depend on decisions not yet made (final schema, real requirements) and will follow.

## Documentation rules
1. Do not document an unimplemented feature as implemented.
2. Use the status legend above where useful.
3. Do not invent MITRC credentials, inventory, SSO configuration, borrowing limits, fines, rack numbers, departments or other institutional data.
4. Major architecture changes require an Architecture Decision Record.
5. API changes require API documentation and tests.
6. Database changes require schema/migration documentation and tests.
7. Security-sensitive behavior must document where it is enforced.
8. Keep terminology consistent with the actual code.

## Documentation-to-code traceability
```text
Requirement → Documentation → Database → API → Backend Service
→ Frontend Service → UI → Tests
```
Example — borrowing: `08-features/borrowing.md` + `09-workflows/borrow-flow.md` → `frontend/services/loanService.js` → `backend/api/loans.py`, `backend/services/loan_service.py`, `backend/repositories/loan_repository.py` → `loans`, `book_copies` tables → tests.
