# Authentication API
**Status:** Planned

| Method | Path | Purpose | Access |
|---|---|---|---|
| POST | `/api/auth/login` | Verify credentials, return secure session/token, include role | Public |
| POST | `/api/auth/logout` | End session | Authenticated |
| GET | `/api/auth/me` | Current user and role | Authenticated |

Errors: `INVALID_CREDENTIALS`, `UNAUTHORIZED`. Rate-limit login. Never return password hashes. Expired sessions must be rejected. Any SSO integration is future scope.
