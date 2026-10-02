# Database Schema
**Status:** Implemented for the current LibSphere dashboard foundation.

Canonical SQL: `database/schema/schema.sql`. Demo data: `database/seed/seed.sql`.

The schema uses PostgreSQL UUID primary keys, enum types, foreign keys and indexes. Book bibliographic records are separate from physical `book_copies`. Department relevance is represented by `book_departments`.
