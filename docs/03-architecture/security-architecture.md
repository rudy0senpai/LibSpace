# Security Architecture
**Status:** Planned. Details: [security overview](../07-security/security-overview.md).

```text
Login → Authentication → Role Detection → Secure Session/Token → Dashboard
```

| Concern | Where enforced |
|---|---|
| Password hashing (Argon2/bcrypt) | `core/security.py`, `services/auth_service.py` |
| Session/token validation | `middleware/auth_middleware.py` |
| Permissions and roles | `core/permissions.py` (central) |
| Input validation | Pydantic `schemas/` |
| SQL injection | Repositories using ORM/parameterized queries |
| Audit trail | `models/audit_log.py`, service layer |
| Secrets | `.env` (git-ignored), `.env.example` |
| Frontend guards | `ProtectedRoute` / `RoleRoute` — UX only |

If MITRC provides an SSO/identity provider later, the auth layer should be able to delegate to it. **No existing SSO is assumed.**
