# Security Overview
**Status:** Planned

Always consider: password hashing · secure sessions/tokens · backend authorization · input validation · parameterized/ORM DB access · XSS prevention · CSRF protection where applicable · rate limiting on sensitive endpoints · file-upload validation · audit logs · least privilege · secret management.

**Never trust frontend-only permissions.**

## Privacy
Never expose passwords, password hashes, session tokens, unnecessary personal data, another user's private notifications or borrowing history. Availability shows aggregate counts, not borrower identity.

See: [authentication](authentication.md) · [RBAC](authorization-rbac.md) · [audit logging](audit-logging.md) · [secrets](secret-management.md) · [checklist](security-checklist.md).
