# Suggestions API
**Status:** Planned

| Method | Path | Purpose | Permission |
|---|---|---|---|
| POST | `/api/suggestions` | Submit (title, author, ISBN optional, category, justification, reason) | SUGGESTION_CREATE |
| GET | `/api/suggestions` | List with vote counts, paginated | authenticated |
| GET | `/api/suggestions/{id}` | Details (librarians also see demand analytics) | authenticated |
| PATCH | `/api/suggestions/{id}` | Change status | SUGGESTION_REVIEW |
| POST | `/api/suggestions/{id}/vote` | Vote (one per user) | SUGGESTION_VOTE |

Error: `SUGGESTION_ALREADY_VOTED`. Status changes notify the submitter and are audit-logged.
