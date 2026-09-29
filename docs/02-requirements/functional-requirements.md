# Functional Requirements
**Status:** Planned. Priority: **M** = MVP must-have, **E** = strong enhancement, **F** = future.

## Authentication & users
| ID | Requirement | Pri |
|---|---|---|
| FR-01 | Users log in and receive a secure session/token; they are not forced to re-login on every visit | M |
| FR-02 | System detects role after login and routes to the matching dashboard | M |
| FR-03 | Passwords are stored only as Argon2/bcrypt hashes | M |
| FR-04 | One common `users` table serves all roles | M |
| FR-05 | Backend enforces authorization on every protected operation | M |
| FR-06 | Librarian/admin can manage users where authorized | E |

## Catalogue & copies
| ID | Requirement | Pri |
|---|---|---|
| FR-10 | Librarian manages books (bibliographic records) incl. authors, categories, publishers | M |
| FR-11 | Librarian manages physical copies (accession no., barcode/QR, shelf, rack, status, condition, acquired date) | M |
| FR-12 | Search by title, author, ISBN, category, publisher, keywords | M |
| FR-13 | Filter by category, author, publisher, year, language, availability, department/relevance, edition; include an **Available Now** filter | M |
| FR-14 | Sort A→Z, Z→A, newest, oldest, most borrowed, recently added (highest rated only if ratings exist) | M |
| FR-15 | Book details page shows cover, title, author, description, ISBN, edition, publisher, year, language, category, rack/shelf, total and available copies, actions | M |
| FR-16 | Details page never reveals who has borrowed a copy; only aggregate counts | M |
| FR-17 | Results are paginated | M |

## Borrowing
| ID | Requirement | Pri |
|---|---|---|
| FR-20 | User can request a book; lifecycle REQUESTED → APPROVED → BORROWED → RETURNED (plus OVERDUE, LOST, DAMAGED, CANCELLED) | M |
| FR-21 | Librarian approves/issues and records returns | M |
| FR-22 | Borrow logic checks eligibility, copy availability, limits, overdue restrictions, computes due date, creates the loan, updates copy status, sends notifications | M |
| FR-23 | Users view current loans, due dates and history (own only) | M |

## Reservations & waiting list
| ID | Requirement | Pri |
|---|---|---|
| FR-30 | If no copy is available, user can reserve / join waiting list | E |
| FR-31 | On return, next eligible user is notified and given a reservation window; if unclaimed, next user | E |

## Suggestions & voting
| ID | Requirement | Pri |
|---|---|---|
| FR-40 | User submits suggestion: title, author, ISBN (optional), category, justification, reason | M |
| FR-41 | Reasons: Course Requirement, Competitive Exam, Research, Programming, Personal Learning, Faculty Recommendation, Other | M |
| FR-42 | Users vote once per suggestion; voting measures demand and never forces a purchase | M |
| FR-43 | Librarian manages suggestion status (SUBMITTED, UNDER_REVIEW, APPROVED, ORDERED, AVAILABLE, REJECTED, DUPLICATE, ALREADY_AVAILABLE) | M |
| FR-44 | Librarian sees supporters, student/faculty split, department distribution, reason categories, date, status | E |

## Notifications, dashboards, reporting
| ID | Requirement | Pri |
|---|---|---|
| FR-50 | In-app notifications: due soon, overdue, reservation available, suggestion status changed, new books added | M |
| FR-51 | Student dashboard: borrowed / due-soon / overdue counts, current loans, reservations, notifications, recent/popular/recommended books, own suggestions | M |
| FR-52 | Librarian dashboard: totals of books, copies, available, borrowed, overdue, lost/damaged, pending suggestions, active users; charts when practical | M |
| FR-53 | Department role sees scoped reports/statistics | E |
| FR-54 | Audit log records WHO / WHAT / WHEN for administrative actions | E (basic logging is in MVP DoD) |
| FR-55 | Fine calculation (NO_FINE, PENDING, WAIVED, PAID); no online payment | E |
| FR-56 | QR/barcode scan identifies a copy for inspect/issue/return/update | E |
| FR-57 | "Find My Book" location path (Library → Block/Floor → Rack → Shelf) | E/F |
| FR-58 | AI recommendations, natural-language search, email, library map, PWA, SSO | F |
