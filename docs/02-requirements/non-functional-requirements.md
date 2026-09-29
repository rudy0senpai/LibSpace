# Non-Functional Requirements
**Status:** Planned

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Security | Hash passwords (Argon2/bcrypt); secure sessions/tokens; backend authorization always enforced; least privilege |
| NFR-02 | Security | Input validation, parameterized/ORM DB access, XSS prevention, CSRF protection where applicable, rate limiting on sensitive endpoints, file-upload validation |
| NFR-03 | Privacy | Never expose password hashes, tokens, unnecessary personal data, other users' notifications or borrowing history; availability is aggregate only |
| NFR-04 | Performance | Paginate books, users, loans, suggestions; index frequently searched fields; never fetch whole datasets for one page |
| NFR-05 | Scalability | No Redis/Elasticsearch/microservices unless requirements justify them |
| NFR-06 | Reliability | Structured errors (see [error codes](../06-api/error-codes.md)), no raw stack traces |
| NFR-07 | Usability | Modern, clean, responsive, accessible UI; dark/light mode; loading and error states |
| NFR-08 | Maintainability | Clean API → Services → Repositories layering; reuse components/services; centralized permissions (no scattered role checks) |
| NFR-09 | Testability | Unit, integration and E2E tests for core workflows |
| NFR-10 | Data integrity | Book ≠ Copy model; one vote per user/suggestion; no silent destructive DB changes |
| NFR-11 | Configuration | Secrets only in `.env` (git-ignored); `.env.example` template |
| NFR-12 | Storage | Files kept in file/object storage; DB stores references/paths |
| NFR-13 | Portability | Docker Compose for frontend/backend/database (planned) |
| NFR-14 | Extensibility | Architecture able to integrate institutional SSO later |
