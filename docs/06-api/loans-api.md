# Loans API
**Status:** Planned

| Method | Path | Purpose | Permission |
|---|---|---|---|
| POST | `/api/loans` | Request/borrow a book | LOAN_CREATE |
| GET | `/api/loans` | Own loans (users) or all (librarian), paginated | scoped |
| GET | `/api/loans/{id}` | View a loan | owner or librarian |
| PATCH | `/api/loans/{id}` | Approve, issue, return, mark lost/damaged, cancel | LOAN_APPROVE / LOAN_RETURN |

Business checks: eligibility, copy availability, limits, overdue restrictions, due date, copy status change, notifications. Errors: `COPY_NOT_AVAILABLE`, `LOAN_LIMIT_REACHED`, `OVERDUE_BOOK_EXISTS`, `FORBIDDEN`. Limits and durations are TBD.
