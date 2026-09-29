# Users API
**Status:** Planned

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/api/users` | List (paginated) | USER_VIEW (librarian/admin) |
| POST | `/api/users` | Create | USER_CREATE |
| GET | `/api/users/{id}` | View | self or USER_VIEW |
| PATCH | `/api/users/{id}` | Update (own profile or authorized) | USER_UPDATE / self |
| DELETE | `/api/users/{id}` | Deactivate/remove | USER_DELETE |

Never expose password hashes or other users' private data.
