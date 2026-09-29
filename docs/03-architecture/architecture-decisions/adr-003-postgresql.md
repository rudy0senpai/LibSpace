# ADR-003: PostgreSQL
**Status:** Accepted
**Decision:** PostgreSQL is the database.
**Consequences:** SQLite only for an explicit dev/test reason, never as the final multi-user architecture. No silent destructive changes; schema changes go through migrations. No Redis/Elasticsearch unless justified.
