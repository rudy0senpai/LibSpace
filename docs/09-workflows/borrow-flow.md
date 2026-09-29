# Borrow Flow
**Status:** Planned
```text
User finds book → (copy available?) yes → Request → Librarian approves → Issue
                                       no  → Reserve / join waiting list
Issue: loan BORROWED, copy BORROWED, due date set, user notified
```
Checks: eligibility, availability, limits (TBD), overdue restrictions (TBD). Errors: `COPY_NOT_AVAILABLE`, `LOAN_LIMIT_REACHED`, `OVERDUE_BOOK_EXISTS`.
