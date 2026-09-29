# Authentication Flow
**Status:** Planned
```text
Login form → POST /api/auth/login → verify hash → detect role → issue secure session/token
→ redirect to role dashboard → subsequent requests authorized on the backend → logout / expiry
```
Failure: `INVALID_CREDENTIALS`. Frontend guards only improve UX.
