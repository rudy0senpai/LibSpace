# MITRC LibSphere — Directory & File Structure

**Project:** MITRC LibSphere  
**Institution:** Modern Institute of Technology and Research Centre, Alwar, Rajasthan  
**Purpose:** Library Management & Discovery Portal  
**Frontend:** React + JavaScript + Vite  
**Backend:** FastAPI + Python  
**Database:** PostgreSQL

---

## Project Structure

```text
MITRC-LibSphere/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── project-overview.md
│   ├── requirements.md
│   ├── architecture.md
│   ├── database-schema.md
│   ├── api-documentation.md
│   ├── roles-and-permissions.md
│   └── workflows.md
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   │
│   ├── public/
│   │   ├── logo/
│   │   │   └── mitrc-logo.png
│   │   └── images/
│   │
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       │
│       ├── components/
│       │   ├── common/
│       │   ├── layout/
│       │   ├── books/
│       │   ├── suggestions/
│       │   ├── notifications/
│       │   └── users/
│       │
│       ├── pages/
│       │   ├── auth/
│       │   ├── student/
│       │   ├── faculty/
│       │   ├── department/
│       │   ├── librarian/
│       │   └── admin/
│       │
│       ├── routes/
│       │   ├── AppRoutes.jsx
│       │   ├── ProtectedRoute.jsx
│       │   └── RoleRoute.jsx
│       │
│       ├── services/
│       │   ├── api.js
│       │   ├── authService.js
│       │   ├── bookService.js
│       │   ├── loanService.js
│       │   ├── suggestionService.js
│       │   └── notificationService.js
│       │
│       ├── context/
│       │   ├── AuthContext.jsx
│       │   ├── ThemeContext.jsx
│       │   └── NotificationContext.jsx
│       │
│       ├── hooks/
│       │   ├── useAuth.js
│       │   ├── useBooks.js
│       │   ├── useLoans.js
│       │   └── useNotifications.js
│       │
│       ├── utils/
│       │   ├── constants.js
│       │   ├── validators.js
│       │   ├── formatters.js
│       │   └── permissions.js
│       │
│       └── styles/
│           ├── globals.css
│           └── themes.css
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   │
│   └── app/
│       ├── main.py
│       │
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py
│       │   ├── database.py
│       │   └── permissions.py
│       │
│       ├── models/
│       │   ├── user.py
│       │   ├── department.py
│       │   ├── book.py
│       │   ├── book_copy.py
│       │   ├── author.py
│       │   ├── category.py
│       │   ├── publisher.py
│       │   ├── loan.py
│       │   ├── reservation.py
│       │   ├── suggestion.py
│       │   ├── suggestion_vote.py
│       │   ├── notification.py
│       │   ├── fine.py
│       │   └── audit_log.py
│       │
│       ├── schemas/
│       │   ├── auth.py
│       │   ├── user.py
│       │   ├── book.py
│       │   ├── loan.py
│       │   ├── reservation.py
│       │   ├── suggestion.py
│       │   └── notification.py
│       │
│       ├── api/
│       │   ├── auth.py
│       │   ├── users.py
│       │   ├── books.py
│       │   ├── book_copies.py
│       │   ├── loans.py
│       │   ├── reservations.py
│       │   ├── suggestions.py
│       │   ├── notifications.py
│       │   ├── reports.py
│       │   └── admin.py
│       │
│       ├── services/
│       │   ├── auth_service.py
│       │   ├── book_service.py
│       │   ├── loan_service.py
│       │   ├── reservation_service.py
│       │   ├── suggestion_service.py
│       │   ├── notification_service.py
│       │   └── report_service.py
│       │
│       ├── repositories/
│       │   ├── user_repository.py
│       │   ├── book_repository.py
│       │   ├── loan_repository.py
│       │   └── suggestion_repository.py
│       │
│       ├── middleware/
│       │   ├── auth_middleware.py
│       │   ├── logging_middleware.py
│       │   └── error_handler.py
│       │
│       └── tests/
│           ├── test_auth.py
│           ├── test_books.py
│           ├── test_loans.py
│           └── test_suggestions.py
│
├── database/
│   ├── migrations/
│   ├── seed/
│   │   ├── departments.sql
│   │   ├── users.sql
│   │   ├── books.sql
│   │   └── sample_data.sql
│   │
│   └── schema/
│       └── database.sql
│
├── scripts/
│   ├── setup.sh
│   ├── seed_database.py
│   └── backup_database.sh
│
└── tests/
    ├── integration/
    └── e2e/
```

---

## Architecture Layers

```text
┌─────────────────────────────────────┐
│             FRONTEND                │
│      React + JavaScript + Vite      │
└──────────────────┬──────────────────┘
                   │
                   │ HTTP / JSON API
                   ▼
┌─────────────────────────────────────┐
│              BACKEND                │
│          FastAPI + Python           │
├─────────────────────────────────────┤
│ API → Services → Repositories       │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│             DATABASE                │
│             PostgreSQL              │
└─────────────────────────────────────┘
```

---

## Main Functional Domains

### Authentication & Authorization

```text
frontend/pages/auth/
frontend/context/AuthContext.jsx
frontend/routes/ProtectedRoute.jsx
frontend/routes/RoleRoute.jsx

backend/api/auth.py
backend/core/security.py
backend/core/permissions.py
backend/services/auth_service.py
backend/models/user.py
```

### Book Catalogue

```text
frontend/components/books/
frontend/pages/student/BookSearch.jsx

backend/api/books.py
backend/api/book_copies.py
backend/services/book_service.py
backend/models/book.py
backend/models/book_copy.py
backend/models/author.py
backend/models/category.py
backend/models/publisher.py
```

### Borrowing & Reservations

```text
frontend/services/loanService.js
frontend/services/reservationService.js

backend/api/loans.py
backend/api/reservations.py
backend/services/loan_service.py
backend/services/reservation_service.py
backend/models/loan.py
backend/models/reservation.py
```

### Book Suggestions & Voting

```text
frontend/components/suggestions/
frontend/services/suggestionService.js

backend/api/suggestions.py
backend/services/suggestion_service.py
backend/models/suggestion.py
backend/models/suggestion_vote.py
```

### Notifications

```text
frontend/components/notifications/
frontend/context/NotificationContext.jsx
frontend/services/notificationService.js

backend/api/notifications.py
backend/services/notification_service.py
backend/models/notification.py
```

### Librarian & Administration

```text
frontend/pages/librarian/
frontend/pages/admin/

backend/api/admin.py
backend/api/reports.py
backend/services/report_service.py
backend/models/audit_log.py
```

---

## Development Order

1. **Project foundation**
   - React + Vite
   - FastAPI
   - PostgreSQL
   - Environment configuration
   - Git repository

2. **Authentication**
   - Login
   - Session/token management
   - Role-based access
   - Protected routes

3. **Book catalogue**
   - Books
   - Physical copies
   - Authors
   - Categories
   - Search
   - Filters
   - Availability

4. **Library transactions**
   - Borrow
   - Return
   - Reservations
   - Due dates
   - Loan history

5. **Community features**
   - Book suggestions
   - Voting
   - Suggestion status

6. **Librarian management**
   - Book management
   - Copy management
   - User management
   - Loan management
   - Reports
   - Audit logs

7. **Polish**
   - Notifications
   - Responsive UI
   - Loading states
   - Error handling
   - Dark mode
   - QR/barcode support

8. **Advanced features**
   - AI recommendations
   - Smart search
   - Analytics
   - Library map
   - PWA/mobile support

---

## Important Design Principles

### Book ≠ Physical Book Copy

A `book` represents the bibliographic work, while `book_copy` represents an individual physical copy.

```text
BOOK
 │
 ├── Copy #001
 ├── Copy #002
 ├── Copy #003
 └── Copy #004
```

### One User System

Students, faculty, librarians and administrators should use a common `users` table with role-based permissions.

```text
users
 ├── STUDENT
 ├── FACULTY
 ├── DEPARTMENT
 ├── LIBRARIAN
 └── ADMIN
```

### Frontend Never Connects Directly to PostgreSQL

```text
React
  ↓
FastAPI API
  ↓
Service Layer
  ↓
Repository Layer
  ↓
PostgreSQL
```

### Secrets Stay Outside Git

Real credentials and secrets belong in `.env`, which must be excluded from version control.

Use `.env.example` as the template.

---

## Initial Project Root

The first implementation milestone should contain only:

```text
MITRC-LibSphere/
│
├── frontend/
├── backend/
├── database/
├── docs/
├── scripts/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

The remaining files and directories should be created progressively as their corresponding features are implemented.
