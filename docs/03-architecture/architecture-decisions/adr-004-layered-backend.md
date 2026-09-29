# ADR-004: Layered backend
**Status:** Accepted
**Decision:** API → Services → Repositories → PostgreSQL. The frontend never accesses the database.
**Rationale:** Clean boundaries, testability, reusable business logic.
**Consequences:** Business rules live in services, not routes or repositories. No microservices.
