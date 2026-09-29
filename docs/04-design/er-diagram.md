# ER Diagram (Conceptual)
**Status:** Planned — conceptual draft. Exact fields are finalized during database design.

```mermaid
erDiagram
    DEPARTMENTS ||--o{ USERS : has
    USERS ||--o{ LOANS : borrows
    USERS ||--o{ RESERVATIONS : places
    USERS ||--o{ SUGGESTIONS : submits
    USERS ||--o{ SUGGESTION_VOTES : casts
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : performs
    SUGGESTIONS ||--o{ SUGGESTION_VOTES : receives
    PUBLISHERS ||--o{ BOOKS : publishes
    CATEGORIES ||--o{ BOOKS : classifies
    BOOKS }o--o{ AUTHORS : written_by
    BOOKS ||--o{ BOOK_COPIES : has
    BOOKS ||--o{ RESERVATIONS : reserved_for
    BOOK_COPIES ||--o{ LOANS : lent_in
    LOANS ||--o| FINES : may_incur
```

## Notes
- `book_authors` is the join table for the many-to-many Book–Author relation.
- Loans reference **copies**, not books (see [ADR-005](../03-architecture/architecture-decisions/adr-005-book-copy-model.md)).
- Reservations refer to a book (and possibly a specific copy) — final choice pending.
- Possible future entities (do not add prematurely): `waitlist_entries`, `book_ratings`, `book_reviews`, `library_locations`, `shelves`, `acquisition_requests`, `system_settings`, `sessions`.
