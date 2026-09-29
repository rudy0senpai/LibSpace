# Business Rules
**Status:** Planned. **Values marked TBD must come from MITRC — do not invent them.**

| ID | Rule |
|---|---|
| BR-01 | A **book** is a bibliographic record; a **book copy** is a physical item. Loans reference copies, not books. |
| BR-02 | A copy may be borrowed only if its status is `AVAILABLE`. |
| BR-03 | Borrow eligibility checks: active user, copy availability, loan limit (TBD), no blocking overdue items (TBD policy), then due-date calculation (loan period TBD). |
| BR-04 | Approving/issuing a loan sets the copy to `BORROWED`; returning sets it back to `AVAILABLE` (or `DAMAGED`/`LOST`/`MAINTENANCE` as appropriate). |
| BR-05 | If no copy is available a user may join the waiting list. On return, the next eligible user is notified and gets a reservation window (length TBD); if unclaimed, the next user is offered the copy. |
| BR-06 | Users see only their own loans, notifications and history. Book pages show aggregate borrowed counts, never borrower identity. |
| BR-07 | One vote per user per suggestion. Voting measures demand and does not force acquisition. |
| BR-08 | Suggestions with an existing catalogue match can be marked `ALREADY_AVAILABLE`; repeats `DUPLICATE`. |
| BR-09 | Fine = overdue days × rate (rate TBD). Statuses `NO_FINE`, `PENDING`, `WAIVED`, `PAID`. The value ₹20 for 4 days in the source material is only an *illustration*. No online payment in MVP. |
| BR-10 | Department role has scoped access and never more DB-management rights than a librarian. |
| BR-11 | Administrative actions (book added, copy status changed, role changed, loan approved, suggestion status changed) are audit-logged. |
| BR-12 | Frontend route protection is cosmetic; every protected operation is authorized on the backend. |
