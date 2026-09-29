# Assumptions and Constraints
**Status:** Planned

## Technology constraints
- React + JavaScript + Vite; **JavaScript, not TypeScript**, unless explicitly instructed.
- FastAPI + Python; PostgreSQL. Do not replace them without explicit approval.
- SQLite only for an explicit dev/test reason, never as the final multi-user database.
- No unnecessary frameworks or microservices.

## Things that must NOT be assumed or invented
MITRC's actual SSO system · the student/faculty database · the library inventory · borrowing limits · fine rules · departments (unless supplied) · librarian accounts · API credentials · institutional email configuration · rack layout · production data.

**Use mock/demo data until real requirements or data are supplied.** If MITRC later provides an SSO/identity provider, the architecture should be able to integrate it.

## Process constraints
- Hackathon timeline: core workflow first; Docker must not delay it.
- Prefer incremental, reviewable changes; preserve working functionality.
- Do not create hundreds of empty files to match the directory tree; create modules as they are implemented.
- No destructive database changes without explicit sign-off.
- Do not add future entities prematurely.

## Open questions (require real MITRC input)
Loan limits and durations · fine rates · reservation window length · department list · identity fields (enrollment/employee IDs) · SSO availability · physical layout for "Find My Book".
