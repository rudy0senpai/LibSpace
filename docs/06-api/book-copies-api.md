# Book Copies API
**Status:** Planned

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/api/books/{id}/copies` | List copies of a book | COPY_VIEW |
| POST | `/api/books/{id}/copies` | Add a copy | COPY_CREATE |
| GET | `/api/book-copies/{id}` | View (also by scanned code, future) | COPY_VIEW |
| PATCH | `/api/book-copies/{id}` | Update status, condition, shelf/rack | COPY_UPDATE |
| DELETE | `/api/book-copies/{id}` | Remove | COPY_DELETE |

Status/condition changes are audit-logged.
