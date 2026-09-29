# Authentication
**Status:** Planned

```text
Login → Authentication → Role Detection → Secure Session/Token → Dashboard
```
- Users are not forced to log in every visit (persistent secure session/token).
- Passwords: never plaintext; Argon2 or bcrypt.
- Login endpoints are rate-limited; expired sessions rejected.
- Admins can revoke sessions.
- Token vs server-side session storage is undecided (a `sessions` table is a possible future entity).
- Institutional SSO: architecture should allow it later; **no existing MITRC SSO is assumed.**
