# Frontend Architecture
**Status:** Planned. Stack: React, JavaScript (`.jsx`, no TypeScript), Vite, Tailwind CSS.

```text
frontend/
├── package.json, package-lock.json, vite.config.js, index.html
├── public/        logo/mitrc-logo.png, images/, icons/, fonts/
└── src/
    ├── main.jsx, App.jsx
    ├── components/  common/ layout/ books/ suggestions/ notifications/ users/
    ├── pages/       auth/ student/ faculty/ department/ librarian/ admin/
    ├── routes/      AppRoutes.jsx ProtectedRoute.jsx RoleRoute.jsx
    ├── services/    api.js authService.js bookService.js loanService.js
    │                reservationService.js suggestionService.js
    │                notificationService.js userService.js reportService.js
    ├── context/     AuthContext.jsx ThemeContext.jsx NotificationContext.jsx
    ├── hooks/       useAuth.js useBooks.js useLoans.js useReservations.js useNotifications.js
    ├── utils/       constants.js validators.js formatters.js permissions.js storage.js
    ├── styles/      globals.css themes.css components.css
    └── assets/      images/ icons/ illustrations/
```

## Responsibilities
| Folder | Role |
|---|---|
| `components/` | Reusable UI grouped by domain |
| `pages/` | Route-level screens per role |
| `routes/` | Route table, login guard (`ProtectedRoute`), role guard (`RoleRoute`) |
| `services/` | All HTTP calls to the API; components never call `fetch` directly |
| `context/` | Auth, theme (dark/light) and notification state |
| `hooks/` | Data-fetching/state hooks wrapping services |
| `utils/` | Constants, validators, formatters, permission helpers, storage helpers |

## Rules
- Route guards are **UX only**; the backend is the security boundary.
- Convert API error codes into human-readable messages.
- Show loading and error states everywhere.
- Reuse components; keep frontend/backend boundaries clean.
- Known page: `pages/student/BookSearch.jsx`; the rest of the page list is decided during frontend build.
