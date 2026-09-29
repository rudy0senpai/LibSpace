# Testing Strategy
**Status:** Planned

| Level | Scope | Location |
|---|---|---|
| Backend unit | Authentication, permissions, availability, borrowing, returns, suggestions, voting, edge cases | `backend/app/tests/` (`test_auth`, `test_books`, `test_loans`, `test_reservations`, `test_suggestions`) |
| Integration | API → service → database | `tests/integration/` (`test_auth_flow`, `test_book_flow`, `test_loan_flow`, `test_suggestion_flow`) |
| End-to-end | Browser workflows, e.g. Login → Search → Request → Approve → Issue → Return | `tests/e2e/` (`login`, `book-search`, `borrowing`, `suggestions` specs) |

Rules: add/update tests for meaningful functionality; API changes need tests; DB changes need tests. Security tests must verify that unauthorized users cannot perform protected operations. Tests use mock data only.
