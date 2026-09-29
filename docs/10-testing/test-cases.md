# Test Cases (Initial Catalogue)
**Status:** Planned

| ID | Case | Expected |
|---|---|---|
| TC-01 | Login with valid credentials | Session issued, role dashboard |
| TC-02 | Login with wrong password | `INVALID_CREDENTIALS` |
| TC-03 | Student calls a librarian-only endpoint | `FORBIDDEN` |
| TC-04 | Unauthenticated call to protected endpoint | `UNAUTHORIZED` |
| TC-05 | Search by title/author/ISBN | Matching paginated results |
| TC-06 | Filter Available Now | Only books with an available copy |
| TC-07 | Book with 4 copies, 1 borrowed | 3 available, 1 borrowed shown as count only |
| TC-08 | Request book with no available copy | `COPY_NOT_AVAILABLE` / reservation offered |
| TC-09 | Librarian approves and issues | Loan BORROWED, copy BORROWED, due date set, notification sent |
| TC-10 | Return | Loan RETURNED, copy AVAILABLE |
| TC-11 | Return overdue book | Fine status PENDING (rate TBD) |
| TC-12 | Vote on suggestion twice | `SUGGESTION_ALREADY_VOTED` |
| TC-13 | Librarian changes suggestion status | Submitter notified, audit log entry |
| TC-14 | User reads another user's notifications/history | Denied |
| TC-15 | Password storage | Only hashes stored |
