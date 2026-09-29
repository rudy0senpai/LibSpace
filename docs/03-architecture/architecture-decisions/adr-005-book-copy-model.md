# ADR-005: Book / Book-copy separation
**Status:** Accepted
**Decision:** `books` holds bibliographic data; `book_copies` holds physical items. Loans reference copies. A single `users` table serves all roles.
**Rationale:** Accurate availability, per-copy status (AVAILABLE, BORROWED, RESERVED, LOST, DAMAGED, MAINTENANCE, WITHDRAWN), QR/barcode per copy.
**Consequences:** Availability = count of `AVAILABLE` copies; borrower identity is never shown publicly.
