# UI/UX Design Direction
**Status:** Planned

The application should feel modern, professional, clean, responsive and accessible.

- Card-based information, clear dashboards, subtle animations, strong visual hierarchy.
- Dark/light mode (`ThemeContext`, `themes.css`).
- Library/book visual identity; logo at `frontend/public/logo/mitrc-logo.png`.
- **Brand palette** (from the project synopsis): deep navy, blue, cyan, purple, white, soft neutral backgrounds. May evolve while staying consistent.
- Loading and error states everywhere; human-readable error messages.
- Styling with Tailwind CSS.

## Screen inventory (planned, by role)
| Role | Screens |
|---|---|
| Auth | Login |
| Student / Faculty | Dashboard, book search/catalogue, book details, my loans/history, reservations, notifications, suggestions list, suggest a book, profile |
| Department | Scoped reports/statistics dashboard |
| Librarian | Dashboard with charts, books, copies, loans/returns, reservations, users, suggestions review, reports, audit logs |
| Admin | Roles/permissions, settings, accounts, sessions, audit |

Only `pages/student/BookSearch.jsx` is named in the blueprint; the final page list is set during frontend design. Future: interactive "Find My Book" library map.
