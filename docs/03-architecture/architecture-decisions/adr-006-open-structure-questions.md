# ADR-006: Open structure questions
**Status:** Proposed (needs owner confirmation)

The two source documents differ slightly. Proposed resolutions:

| Question | Proposal |
|---|---|
| Where do migrations live? `database/migrations/` vs `backend/alembic.ini` | Alembic owns migrations under the backend; `database/schema/database.sql` is a reference snapshot; `database/migrations/README.md` points to Alembic |
| Flat `docs/*.md` vs numbered `docs/01-…15-…/` | Use the numbered structure (this set) |
| Missing reservation files in the early tree (`reservationService.js`, `useReservations.js`, `reservation_repository.py`, `test_reservations.py`) | Treat the detailed trees as authoritative |
| `sessions` table vs stateless tokens | Undecided — `sessions` is a possible future entity; decide with the auth design |
