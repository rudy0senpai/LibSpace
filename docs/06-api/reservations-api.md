# Reservations API
**Status:** Planned (strong enhancement)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/reservations` | Join waiting list for an unavailable book |
| GET | `/api/reservations` | Own reservations (librarian: all) |
| GET | `/api/reservations/{id}` | View |
| DELETE | `/api/reservations/{id}` | Cancel |

Error: `RESERVATION_NOT_ALLOWED`. Flow: [reservation flow](../09-workflows/reservation-flow.md).
