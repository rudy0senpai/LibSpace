# Books API
**Status:** Planned

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/api/books` | Search, filter, sort, paginate | BOOK_VIEW |
| GET | `/api/books/{id}` | Details with total/available copies and rack/shelf | BOOK_VIEW |
| POST | `/api/books` | Create | BOOK_CREATE |
| PATCH | `/api/books/{id}` | Update | BOOK_UPDATE |
| DELETE | `/api/books/{id}` | Delete | BOOK_DELETE |

**Query parameters (planned):** search text (title, author, ISBN, category, publisher, keywords); filters: category, author, publisher, year, language, availability (*Available Now*), department, edition; sort: A→Z, Z→A, newest, oldest, most borrowed, recently added; page and page size.

Responses expose aggregate borrowed counts only, never borrower identity. Error: `BOOK_NOT_FOUND`.
