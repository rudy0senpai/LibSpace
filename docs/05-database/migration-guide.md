# Migration Guide
**Status:** Planned

1. Change order: Model → Migration → Schema → Repository → Service → API → Frontend.
2. Never make destructive changes silently; call them out for review.
3. Document each schema change in `database-schema.md` and add tests.
4. Tool: Alembic (`backend/alembic.ini`) is proposed; `database/migrations/` gets a README. See [ADR-006](../03-architecture/architecture-decisions/adr-006-open-structure-questions.md).
5. Reference schema snapshot: `database/schema/database.sql`.
