# Data Flow
**Status:** Planned

```text
React → HTTP/JSON → FastAPI → API layer → Service layer → Repository layer → PostgreSQL
```

## Example: request a book
1. UI (`BookDetails`) calls `loanService.js`.
2. `POST /api/loans` reaches `api/loans.py`; auth middleware resolves the user and role.
3. `loan_service.py` checks eligibility, copy availability, limits and overdue status.
4. `loan_repository.py` writes the loan (status `REQUESTED`).
5. `notification_service.py` notifies the librarian.
6. The response returns the loan; the UI refreshes dashboard data.

## Central lifecycle
```text
DISCOVER → BORROW → RETURN → SUGGEST → VOTE → ACQUIRE → DISCOVER
```
