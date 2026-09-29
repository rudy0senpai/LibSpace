# Security Checklist
**Status:** Planned

- [ ] Passwords hashed with Argon2/bcrypt
- [ ] Secure session/token handling, expiry validated
- [ ] Backend authorization on every protected endpoint
- [ ] Central permission checks (no scattered role checks)
- [ ] Input validation on all requests
- [ ] ORM / parameterized queries only
- [ ] XSS prevention; CSRF protection where applicable
- [ ] Rate limiting on login and sensitive endpoints
- [ ] File upload validation (type, size); DB stores references only
- [ ] No hashes, tokens or other users' data in responses
- [ ] Audit logging for administrative actions
- [ ] `.env` git-ignored; no secrets in the repo
- [ ] Structured errors without stack traces
- [ ] Least privilege for roles and DB user
