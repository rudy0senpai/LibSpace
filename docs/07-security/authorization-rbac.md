# Authorization and RBAC
**Status:** Planned. Backend enforcement is mandatory; frontend guards are UX only.

## Roles
| Role | Summary |
|---|---|
| STUDENT | Search/filter/sort, view availability/details, request/borrow/reserve per library rules, own loans/history, notifications, suggest, vote, own profile. Cannot manage catalogue, users, approve loans, or touch the database. |
| FACULTY | Same user-level permissions as students. No library administration. |
| DEPARTMENT | Scoped department reports/statistics and relevant library data. Never broader management rights than the librarian. |
| LIBRARIAN | Manage books, copies, authors/categories/publishers, loans, returns, reservations, waiting lists, users where appropriate, suggestions, reports, analytics, inventory, fines, audit logs. |
| ADMIN / Super Admin | Roles, permissions, system settings, librarian/admin accounts, session revocation, security/audit management. |

## Permission catalogue (centralized)
```text
BOOK_VIEW BOOK_CREATE BOOK_UPDATE BOOK_DELETE
COPY_VIEW COPY_CREATE COPY_UPDATE COPY_DELETE
LOAN_CREATE LOAN_APPROVE LOAN_RETURN
USER_VIEW USER_CREATE USER_UPDATE USER_DELETE
SUGGESTION_CREATE SUGGESTION_VOTE SUGGESTION_REVIEW
REPORT_VIEW AUDIT_VIEW
```
Implemented in `backend/app/core/permissions.py`; avoid scattered hard-coded role checks.

## Role–permission matrix (proposed; to be confirmed)
| Permission | Student | Faculty | Department | Librarian | Admin |
|---|:-:|:-:|:-:|:-:|:-:|
| BOOK_VIEW, COPY_VIEW | ✔ | ✔ | ✔ | ✔ | ✔ |
| BOOK_/COPY_ CREATE/UPDATE/DELETE | | | | ✔ | ✔ |
| LOAN_CREATE | ✔ | ✔ | | ✔ | ✔ |
| LOAN_APPROVE, LOAN_RETURN | | | | ✔ | ✔ |
| USER_* | | | | ✔ (where appropriate) | ✔ |
| SUGGESTION_CREATE, SUGGESTION_VOTE | ✔ | ✔ | | ✔ | ✔ |
| SUGGESTION_REVIEW | | | | ✔ | ✔ |
| REPORT_VIEW | | | scoped | ✔ | ✔ |
| AUDIT_VIEW | | | | ✔ | ✔ |
