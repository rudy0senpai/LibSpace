# Database Schema (Conceptual)
**Status:** Planned. **Draft, not final.** Field lists come from the source documents ("possible fields"); types, constraints and exact columns are decided in the ER/schema design step.

## users
`id, name, email, password_hash, role, department_id, enrollment_id, employee_id, is_active, created_at, updated_at`
Identity fields will be refined when real MITRC requirements are known.

## books
`id, isbn, title, subtitle, description, publication_year, edition, language, cover_image_ref, publisher_id, category_id, department/relevance metadata, created_at, updated_at` (+ authors via join table)

## book_copies
`copy_id, book_id, accession_number, barcode/qr_code, shelf, rack, status, condition, acquired_at`

## loans
`loan_id, user_id, book_copy_id, issued_at, due_at, returned_at, status, issued_by, returned_to, created_at, updated_at`

## reservations
Waiting-list/reservation record per user and book (fields TBD).

## suggestions
`title, author, isbn (optional), category, justification, reason, status, submitter, created_at` (+ reviewer data TBD)

## suggestion_votes
`suggestion_id, user_id` — unique together.

## notifications, fines, audit_logs
- notifications: recipient, type, message, read state, timestamp.
- fines: loan reference, overdue days, amount, status (`NO_FINE`, `PENDING`, `WAIVED`, `PAID`).
- audit_logs: **WHO, WHAT, WHEN** (plus target).

## authors, categories, publishers, departments
Simple lookup entities. Department list must be supplied by MITRC.
