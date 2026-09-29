# Backend Architecture
**Status:** Planned. Stack: FastAPI + Python; PostgreSQL.

```text
backend/
├── requirements.txt, .env.example, alembic.ini
└── app/
    ├── main.py
    ├── core/          config.py security.py database.py permissions.py
    ├── models/        user department book book_copy author category publisher
    │                  loan reservation suggestion suggestion_vote notification fine audit_log
    ├── schemas/       auth user book loan reservation suggestion notification
    ├── api/           auth users books book_copies loans reservations
    │                  suggestions notifications reports admin
    ├── services/      auth book loan reservation suggestion notification report
    ├── repositories/  user book loan reservation suggestion
    ├── middleware/    auth_middleware logging_middleware error_handler
    └── tests/         test_auth test_books test_loans test_reservations test_suggestions
```
(each entry above is a `.py` module; suffixes shortened for readability)

## Layers
```text
API / Routes        → HTTP, validation, auth dependency, calls services
Services            → business logic (eligibility, due dates, status changes, notifications)
Repositories        → data access to PostgreSQL
Models / Schemas    → DB entities / request-response contracts
Core                → config, security (hashing, tokens), DB session, central permissions
Middleware          → authentication, request logging, structured error handling
```

## Rules
- Enforce authorization in the backend; use centralized permissions instead of hard-coded role checks.
- Use ORM or parameterized queries only.
- Return structured errors, never raw stack traces.
- Paginate list endpoints.
- Database change order: Model → Migration → Schema → Repository → Service → API → Frontend.
