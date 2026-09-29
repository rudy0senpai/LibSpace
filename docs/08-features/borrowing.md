# Feature: Borrowing
**Status:** Planned · **Priority:** MVP
Lifecycle `REQUESTED → APPROVED → BORROWED → RETURNED` (others: OVERDUE, LOST, DAMAGED, CANCELLED). Loan data: loan_id, user_id, book_copy_id, issued_at, due_at, returned_at, status, issued_by, returned_to, created_at, updated_at. Logic checks eligibility, availability, limits, overdue restrictions, due date, creates loan, updates copy status, notifies. Limits and durations: **TBD by MITRC.** Flow: [borrow flow](../09-workflows/borrow-flow.md).
