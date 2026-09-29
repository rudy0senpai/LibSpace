# Error Codes
**Status:** Planned. Errors are structured (code + message), never raw stack traces. The frontend maps codes to human-readable messages.

| Code | Meaning |
|---|---|
| BOOK_NOT_FOUND | No such book |
| COPY_NOT_AVAILABLE | No available copy |
| LOAN_LIMIT_REACHED | User reached borrow limit |
| OVERDUE_BOOK_EXISTS | Overdue item blocks borrowing |
| UNAUTHORIZED | Not authenticated |
| FORBIDDEN | Authenticated but not permitted |
| INVALID_CREDENTIALS | Login failed |
| SUGGESTION_ALREADY_VOTED | Duplicate vote |
| RESERVATION_NOT_ALLOWED | Reservation not permitted |
