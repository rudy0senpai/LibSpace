# Software Requirements Specification (SRS)
**Status:** Planned

## 1. Purpose
Specify the requirements of MITRC LibSphere, a web-based library management and discovery portal.

## 2. Scope
See [project scope](../01-project/project-scope.md). Users: students, faculty, departments, librarians, admins.

## 3. Overall description
- **Product perspective:** standalone web application: React SPA → FastAPI REST API → PostgreSQL.
- **User classes:** [roles](../07-security/authorization-rbac.md).
- **Operating environment:** modern browsers (frontend); Python/FastAPI server; PostgreSQL.
- **Constraints:** [assumptions and constraints](../01-project/assumptions-and-constraints.md).

## 4. Functional requirements
See [functional requirements](functional-requirements.md) (IDs FR-xx).

## 5. Non-functional requirements
See [non-functional requirements](non-functional-requirements.md) (IDs NFR-xx).

## 6. External interfaces
- **UI:** responsive, card-based, dark/light mode ([UI/UX](../14-ui-ux/design-system.md)).
- **API:** JSON over HTTP ([API overview](../06-api/api-overview.md)).
- **Storage:** PostgreSQL; uploaded files (e.g. book covers) via file/object storage with references in the DB.
- **Future:** institutional SSO, email — not assumed to exist.

## 7. Data requirements
[Database overview](../05-database/database-overview.md).

## 8. Business rules
[Business rules](business-rules.md).

## 9. Acceptance
[Acceptance criteria](acceptance-criteria.md).
