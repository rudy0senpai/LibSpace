# Relationships
**Status:** Planned

| From | To | Cardinality |
|---|---|---|
| Department | User | 1 : N |
| Publisher | Book | 1 : N |
| Category | Book | 1 : N |
| Book | Author | N : M (join table) |
| Book | Book copy | 1 : N |
| User | Loan | 1 : N |
| Book copy | Loan | 1 : N |
| User | Reservation | 1 : N |
| Book | Reservation | 1 : N |
| User | Suggestion | 1 : N |
| Suggestion | Suggestion vote | 1 : N (unique per user) |
| User | Notification | 1 : N |
| Loan | Fine | 1 : 0..1 |
| User | Audit log | 1 : N |

See the [ER diagram](../04-design/er-diagram.md).
