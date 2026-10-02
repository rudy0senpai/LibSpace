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


---

# Complete Documentation Blueprint

This section expands the existing repository structure into a complete documentation system while preserving the existing React + JavaScript + Vite, FastAPI + Python, and PostgreSQL architecture.

## Documentation Tree

```text
docs/
├── README.md
├── 01-project/
│   ├── project-overview.md
│   ├── project-objectives.md
│   ├── project-scope.md
│   ├── stakeholders.md
│   ├── assumptions-and-constraints.md
│   ├── glossary.md
│   └── roadmap.md
├── 02-requirements/
│   ├── software-requirements-specification.md
│   ├── functional-requirements.md
│   ├── non-functional-requirements.md
│   ├── user-stories.md
│   ├── use-cases.md
│   ├── acceptance-criteria.md
│   ├── requirements-traceability-matrix.md
│   └── business-rules.md
├── 03-architecture/
│   ├── system-architecture.md
│   ├── application-architecture.md
│   ├── frontend-architecture.md
│   ├── backend-architecture.md
│   ├── security-architecture.md
│   ├── data-flow.md
│   ├── integration-architecture.md
│   └── architecture-decisions/
│       ├── README.md
│       ├── adr-001-frontend-stack.md
│       ├── adr-002-backend-stack.md
│       ├── adr-003-postgresql.md
│       ├── adr-004-layered-backend.md
│       └── adr-005-book-copy-model.md
├── 04-design/
│   ├── system-context-diagram.md
│   ├── component-diagram.md
│   ├── sequence-diagrams.md
│   ├── activity-diagrams.md
│   ├── state-diagrams.md
│   ├── deployment-diagram.md
│   └── er-diagram.md
├── 05-database/
│   ├── database-overview.md
│   ├── database-schema.md
│   ├── table-documentation.md
│   ├── relationships.md
│   ├── indexes.md
│   ├── constraints.md
│   ├── enums-and-statuses.md
│   ├── seed-data.md
│   ├── migration-guide.md
│   └── backup-and-restore.md
├── 06-api/
│   ├── api-overview.md
│   ├── authentication-api.md
│   ├── users-api.md
│   ├── books-api.md
│   ├── book-copies-api.md
│   ├── loans-api.md
│   ├── reservations-api.md
│   ├── suggestions-api.md
│   ├── notifications-api.md
│   ├── reports-api.md
│   ├── admin-api.md
│   ├── error-codes.md
│   └── api-examples.md
├── 07-security/
│   ├── security-overview.md
│   ├── authentication.md
│   ├── authorization-rbac.md
│   ├── password-security.md
│   ├── session-management.md
│   ├── input-validation.md
│   ├── api-security.md
│   ├── file-upload-security.md
│   ├── audit-logging.md
│   ├── secret-management.md
│   └── security-checklist.md
├── 08-features/
│   ├── authentication.md
│   ├── user-management.md
│   ├── book-catalogue.md
│   ├── book-copies-and-inventory.md
│   ├── search-filter-sort.md
│   ├── borrowing.md
│   ├── returns.md
│   ├── reservations.md
│   ├── waitlist.md
│   ├── suggestions.md
│   ├── suggestion-voting.md
│   ├── notifications.md
│   ├── fines.md
│   ├── reports-and-analytics.md
│   ├── audit-logs.md
│   └── qr-barcode.md
├── 09-workflows/
│   ├── authentication-flow.md
│   ├── book-discovery-flow.md
│   ├── borrow-flow.md
│   ├── return-flow.md
│   ├── reservation-flow.md
│   ├── waitlist-flow.md
│   ├── suggestion-flow.md
│   ├── voting-flow.md
│   ├── notification-flow.md
│   ├── librarian-workflow.md
│   └── end-to-end-demo-flow.md
├── 10-testing/
│   ├── testing-strategy.md
│   ├── unit-testing.md
│   ├── integration-testing.md
│   ├── api-testing.md
│   ├── frontend-testing.md
│   ├── e2e-testing.md
│   ├── security-testing.md
│   ├── performance-testing.md
│   ├── test-data.md
│   └── test-cases.md
├── 11-deployment/
│   ├── deployment-overview.md
│   ├── local-development.md
│   ├── environment-variables.md
│   ├── docker.md
│   ├── frontend-deployment.md
│   ├── backend-deployment.md
│   ├── database-deployment.md
│   ├── production-checklist.md
│   └── rollback.md
├── 12-development/
│   ├── development-setup.md
│   ├── coding-conventions.md
│   ├── frontend-conventions.md
│   ├── backend-conventions.md
│   ├── database-conventions.md
│   ├── git-workflow.md
│   ├── branch-strategy.md
│   ├── commit-conventions.md
│   └── pull-request-guide.md
├── 13-operations/
│   ├── operations-overview.md
│   ├── monitoring.md
│   ├── logging.md
│   ├── backup-and-recovery.md
│   ├── incident-response.md
│   ├── maintenance.md
│   └── troubleshooting.md
├── 14-ui-ux/
│   ├── design-system.md
│   ├── visual-identity.md
│   ├── layout-guidelines.md
│   ├── accessibility.md
│   ├── responsive-design.md
│   ├── navigation.md
│   └── screen-inventory.md
└── 15-project-management/
    ├── development-phases.md
    ├── feature-priorities.md
    ├── milestone-plan.md
    ├── demo-plan.md
    ├── hackathon-checklist.md
    └── future-scope.md
```

## What Each Documentation Group Covers

### 01-project
Project identity, objectives, scope, stakeholders, terminology, assumptions, and roadmap.

### 02-requirements
SRS, functional/non-functional requirements, user stories, use cases, acceptance criteria, traceability, and business rules.

### 03-architecture
System, application, frontend, backend, security, data-flow, integrations, and Architecture Decision Records.

### 04-design
Version-controlled technical diagrams: context, components, sequence, activity, state, deployment, and ER diagrams.

### 05-database
PostgreSQL schema, tables, relationships, indexes, constraints, statuses, seed data, migrations, backup and restore.

### 06-api
Endpoint-by-endpoint API documentation including authentication, request/response schemas, permissions, validation, errors, and examples.

### 07-security
Authentication, RBAC, password/session security, validation, API/file security, audit logging, secrets, and security checklist.

### 08-features
One authoritative document for each major user-facing or administrative feature.

### 09-workflows
Business-process documentation from authentication through borrowing, returns, reservations, suggestions, voting, notifications, and the complete demo flow.

### 10-testing
Unit, integration, API, frontend, E2E, security, performance, test data, and formal test cases.

### 11-deployment
Local setup, environment configuration, Docker, deployment of each application layer, production checklist, and rollback.

### 12-development
Coding standards, Git strategy, branch/commit conventions, pull requests, and development setup.

### 13-operations
Monitoring, logging, backups, incident response, maintenance, and troubleshooting.

### 14-ui-ux
Design system, visual identity, layout, accessibility, responsive behavior, navigation, and complete screen inventory.

### 15-project-management
Development phases, priorities, milestones, demo preparation, hackathon readiness, and future scope.

---

# Frontend — Detailed Internal Structure

The existing frontend organization is preserved: `public/` for public assets and `src/` for application code, with components, pages, routes, services, context, hooks, utilities, and styles separated by responsibility.

```text
frontend/
├── package.json
├── package-lock.json
├── vite.config.js
├── index.html
├── public/
│   ├── logo/
│   │   └── mitrc-logo.png
│   ├── images/
│   ├── icons/
│   └── fonts/
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── components/
    │   ├── common/
    │   ├── layout/
    │   ├── books/
    │   ├── suggestions/
    │   ├── notifications/
    │   └── users/
    ├── pages/
    │   ├── auth/
    │   ├── student/
    │   ├── faculty/
    │   ├── department/
    │   ├── librarian/
    │   └── admin/
    ├── routes/
    │   ├── AppRoutes.jsx
    │   ├── ProtectedRoute.jsx
    │   └── RoleRoute.jsx
    ├── services/
    │   ├── api.js
    │   ├── authService.js
    │   ├── bookService.js
    │   ├── loanService.js
    │   ├── reservationService.js
    │   ├── suggestionService.js
    │   ├── notificationService.js
    │   ├── userService.js
    │   └── reportService.js
    ├── context/
    │   ├── AuthContext.jsx
    │   ├── ThemeContext.jsx
    │   └── NotificationContext.jsx
    ├── hooks/
    │   ├── useAuth.js
    │   ├── useBooks.js
    │   ├── useLoans.js
    │   ├── useReservations.js
    │   └── useNotifications.js
    ├── utils/
    │   ├── constants.js
    │   ├── validators.js
    │   ├── formatters.js
    │   ├── permissions.js
    │   └── storage.js
    ├── styles/
    │   ├── globals.css
    │   ├── themes.css
    │   └── components.css
    └── assets/
        ├── images/
        ├── icons/
        └── illustrations/
```

---

# Backend — Detailed Internal Structure

The existing backend organization is preserved: core configuration/security, models, schemas, API routes, services, repositories, middleware, and tests.

```text
backend/
├── requirements.txt
├── .env.example
├── alembic.ini
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   ├── security.py
    │   ├── database.py
    │   └── permissions.py
    ├── models/
    │   ├── user.py
    │   ├── department.py
    │   ├── book.py
    │   ├── book_copy.py
    │   ├── author.py
    │   ├── category.py
    │   ├── publisher.py
    │   ├── loan.py
    │   ├── reservation.py
    │   ├── suggestion.py
    │   ├── suggestion_vote.py
    │   ├── notification.py
    │   ├── fine.py
    │   └── audit_log.py
    ├── schemas/
    │   ├── auth.py
    │   ├── user.py
    │   ├── book.py
    │   ├── loan.py
    │   ├── reservation.py
    │   ├── suggestion.py
    │   └── notification.py
    ├── api/
    │   ├── auth.py
    │   ├── users.py
    │   ├── books.py
    │   ├── book_copies.py
    │   ├── loans.py
    │   ├── reservations.py
    │   ├── suggestions.py
    │   ├── notifications.py
    │   ├── reports.py
    │   └── admin.py
    ├── services/
    │   ├── auth_service.py
    │   ├── book_service.py
    │   ├── loan_service.py
    │   ├── reservation_service.py
    │   ├── suggestion_service.py
    │   ├── notification_service.py
    │   └── report_service.py
    ├── repositories/
    │   ├── user_repository.py
    │   ├── book_repository.py
    │   ├── loan_repository.py
    │   ├── reservation_repository.py
    │   └── suggestion_repository.py
    ├── middleware/
    │   ├── auth_middleware.py
    │   ├── logging_middleware.py
    │   └── error_handler.py
    └── tests/
        ├── test_auth.py
        ├── test_books.py
        ├── test_loans.py
        ├── test_reservations.py
        └── test_suggestions.py
```

---

# Database Structure

The existing database organization remains:

```text
database/
├── migrations/
│   └── README.md
├── schema/
│   └── database.sql
└── seed/
    ├── departments.sql
    ├── users.sql
    ├── books.sql
    └── sample_data.sql
```

The conceptual model already separates a bibliographic `BOOK` from individual `BOOK_COPY` records, while loans reference physical copies. This separation should remain the basis of inventory and borrowing.

---

# Scripts Structure

```text
scripts/
├── setup.sh
├── seed_database.py
└── backup_database.sh
```

Responsibilities:

- `setup.sh`: development environment setup.
- `seed_database.py`: development/demo data loading.
- `backup_database.sh`: PostgreSQL backup.

---

# Testing Structure

```text
tests/
├── integration/
│   ├── test_auth_flow.py
│   ├── test_book_flow.py
│   ├── test_loan_flow.py
│   └── test_suggestion_flow.py
└── e2e/
    ├── login.spec.js
    ├── book-search.spec.js
    ├── borrowing.spec.js
    └── suggestions.spec.js
```

Use:

- backend tests for isolated backend behavior;
- integration tests for API → service → database behavior;
- E2E tests for complete browser workflows.

---

# Root-Level Documentation Files

```text
README.md
LICENSE
CONTRIBUTING.md
CHANGELOG.md
SECURITY.md
.gitignore
.env.example
docker-compose.yml
```

## README.md

Should cover:

1. Project overview
2. Problem statement
3. Solution
4. Features
5. User roles
6. Technology stack
7. Architecture
8. Directory structure
9. Installation
10. Environment setup
11. Database setup
12. Running frontend
13. Running backend
14. Testing
15. Demo
16. Contribution
17. License
18. Future scope

## CONTRIBUTING.md

Development workflow, coding standards, Git workflow, testing, pull requests, and documentation rules.

## CHANGELOG.md

Versioned record of added, changed, fixed, removed, and security-related changes.

## SECURITY.md

Security policy and vulnerability-reporting procedure.

---

# Documentation-to-Code Rule

Every major feature should be traceable:

```text
Requirement
    ↓
Documentation
    ↓
Database
    ↓
API
    ↓
Backend Service
    ↓
Frontend Service
    ↓
UI
    ↓
Tests
```

For example, borrowing should map to:

```text
docs/08-features/borrowing.md
docs/09-workflows/borrow-flow.md
        ↓
frontend/services/loanService.js
        ↓
backend/api/loans.py
backend/services/loan_service.py
backend/repositories/loan_repository.py
        ↓
database/loans
database/book_copies
        ↓
tests/
```

---

# Documentation Rules

1. Do not document an unimplemented feature as implemented.
2. Use `Planned`, `In Progress`, `Implemented`, `Tested`, and `Deprecated` where useful.
3. Do not invent real MITRC credentials, inventory, SSO configuration, borrowing limits, fines, rack numbers, or other institutional data.
4. Major architecture changes require an Architecture Decision Record.
5. API changes require API documentation and tests.
6. Database changes require schema/migration documentation and tests.
7. Security-sensitive behavior must be documented with its enforcement location.
8. Keep documentation terminology consistent with the actual code.

---

# Minimum Documentation Before Hackathon Demo

If implementation time is limited, the minimum high-value set is:

```text
README.md

docs/
├── README.md
├── 01-project/
│   ├── project-overview.md
│   ├── project-scope.md
│   └── roadmap.md
├── 02-requirements/
│   ├── software-requirements-specification.md
│   ├── functional-requirements.md
│   ├── non-functional-requirements.md
│   └── user-stories.md
├── 03-architecture/
│   ├── system-architecture.md
│   ├── frontend-architecture.md
│   ├── backend-architecture.md
│   └── architecture-decisions/
├── 04-design/
│   ├── er-diagram.md
│   ├── system-context-diagram.md
│   └── sequence-diagrams.md
├── 05-database/
│   ├── database-schema.md
│   ├── relationships.md
│   └── enums-and-statuses.md
├── 06-api/
│   ├── api-overview.md
│   ├── authentication-api.md
│   ├── books-api.md
│   ├── loans-api.md
│   └── suggestions-api.md
├── 07-security/
│   ├── security-overview.md
│   ├── authorization-rbac.md
│   └── security-checklist.md
├── 08-features/
│   ├── authentication.md
│   ├── book-catalogue.md
│   ├── borrowing.md
│   ├── reservations.md
│   ├── suggestions.md
│   └── notifications.md
├── 09-workflows/
│   ├── borrow-flow.md
│   ├── return-flow.md
│   ├── suggestion-flow.md
│   └── end-to-end-demo-flow.md
├── 10-testing/
│   ├── testing-strategy.md
│   └── test-cases.md
└── 11-deployment/
    ├── local-development.md
    └── environment-variables.md
```

---

# Final Architecture Principle

The repository should maintain these boundaries:

```text
MITRC-LibSphere
│
├── docs        → project knowledge and engineering documentation
├── frontend    → React user interface
├── backend     → FastAPI application and business logic
├── database    → PostgreSQL schema, migrations and seed data
├── scripts     → setup/automation/backup
└── tests       → integration and end-to-end verification
```

Runtime data flow:

```text
React
  ↓ HTTP / JSON
FastAPI
  ↓
API Layer
  ↓
Service Layer
  ↓
Repository Layer
  ↓
PostgreSQL
```

The frontend must not connect directly to PostgreSQL.

This file is the **master documentation and directory blueprint**. Individual documentation files become authoritative for their own subject as implementation progresses.
