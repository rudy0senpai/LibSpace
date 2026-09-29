# API Overview
**Status:** Planned. **Contracts are conceptual and will be finalized after the ER/database design.**

- REST over HTTP, JSON bodies, prefix `/api`.
- Auth: secure session/token; protected endpoints enforce permissions on the backend.
- Pagination on books, users, loans, suggestions.
- Errors: structured (see [error codes](error-codes.md)).

## Endpoint map
```text
/api/auth/login | /api/auth/logout | /api/auth/me
/api/users, /api/users/{id}
/api/books, /api/books/{id}, /api/books/{id}/copies
/api/book-copies/{id}
/api/loans, /api/loans/{id}
/api/reservations, /api/reservations/{id}
/api/suggestions, /api/suggestions/{id}, /api/suggestions/{id}/vote
/api/notifications
/api/reports
/api/admin
```
Backend modules: `api/{auth,users,books,book_copies,loans,reservations,suggestions,notifications,reports,admin}.py`.
Rule: any API change requires documentation and tests.
