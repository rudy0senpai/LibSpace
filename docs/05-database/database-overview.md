# Database Overview
**Status:** Planned. Engine: PostgreSQL.

## Initial entities
```text
users, departments
books, book_copies, authors, categories, publishers
loans, reservations
suggestions, suggestion_votes
notifications, fines, audit_logs
```

## Design rules
- One `users` table for all roles (no per-role auth tables).
- **Book ≠ Book copy.**
- Store file references/paths, not binaries.
- Index frequently searched fields; paginate.
- Changes flow Model → Migration → Schema → Repository → Service → API → Frontend.
- No silent destructive changes.
- No future entities prematurely.

## Repository layout
```text
database/
├── migrations/   (README pointing to the migration tool; see ADR-006)
├── schema/database.sql   reference schema (not yet written)
└── seed/         departments.sql users.sql books.sql sample_data.sql
```
