-- MITRC LibSphere PostgreSQL schema
-- Source of truth for the database-driven Department Dashboard.
-- Requires PostgreSQL 14+.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP VIEW IF EXISTS v_department_book_relevance CASCADE;
DROP TABLE IF EXISTS audit_logs, fines, notifications, suggestion_votes, suggestions,
    reservations, loans, book_copies, book_departments, book_authors, books,
    authors, publishers, categories, users, departments CASCADE;
DROP TYPE IF EXISTS role_type, copy_status, loan_status, reservation_status,
    suggestion_status, suggestion_reason, fine_status, notification_type CASCADE;

CREATE TYPE role_type AS ENUM ('STUDENT','FACULTY','DEPARTMENT','LIBRARIAN','ADMIN');
CREATE TYPE copy_status AS ENUM ('AVAILABLE','BORROWED','RESERVED','LOST','DAMAGED','MAINTENANCE','WITHDRAWN');
CREATE TYPE loan_status AS ENUM ('REQUESTED','APPROVED','BORROWED','RETURNED','OVERDUE','LOST','DAMAGED','CANCELLED');
CREATE TYPE reservation_status AS ENUM ('WAITING','ACTIVE','FULFILLED','CANCELLED','EXPIRED');
CREATE TYPE suggestion_status AS ENUM ('SUBMITTED','UNDER_REVIEW','APPROVED','ORDERED','AVAILABLE','REJECTED','DUPLICATE','ALREADY_AVAILABLE');
CREATE TYPE suggestion_reason AS ENUM ('COURSE_REQUIREMENT','COMPETITIVE_EXAM','RESEARCH','PROGRAMMING','PERSONAL_LEARNING','FACULTY_RECOMMENDATION','OTHER');
CREATE TYPE fine_status AS ENUM ('NO_FINE','PENDING','WAIVED','PAID');
CREATE TYPE notification_type AS ENUM ('DUE_SOON','OVERDUE','RESERVATION_AVAILABLE','SUGGESTION_STATUS_CHANGED','NEW_BOOK','SYSTEM');

CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL UNIQUE,
    short_name VARCHAR(80) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role role_type NOT NULL,
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    enrollment_id VARCHAR(50),
    employee_id VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((role IN ('STUDENT','FACULTY','DEPARTMENT') AND department_id IS NOT NULL) OR role IN ('LIBRARIAN','ADMIN'))
);

CREATE TABLE publishers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    website VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(180) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isbn VARCHAR(20) UNIQUE,
    title VARCHAR(300) NOT NULL,
    subtitle VARCHAR(300),
    description TEXT,
    publication_year INTEGER CHECK (publication_year BETWEEN 1400 AND 2100),
    edition VARCHAR(80),
    language VARCHAR(80) NOT NULL DEFAULT 'English',
    cover_image_ref VARCHAR(500),
    publisher_id UUID REFERENCES publishers(id) ON DELETE SET NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE book_authors (
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, author_id)
);

CREATE TABLE book_departments (
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    relevance SMALLINT NOT NULL DEFAULT 1 CHECK (relevance BETWEEN 1 AND 5),
    PRIMARY KEY (book_id, department_id)
);

CREATE TABLE book_copies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    accession_number VARCHAR(50) NOT NULL UNIQUE,
    barcode VARCHAR(100) NOT NULL UNIQUE,
    rack VARCHAR(80) NOT NULL,
    shelf VARCHAR(80) NOT NULL,
    status copy_status NOT NULL DEFAULT 'AVAILABLE',
    condition VARCHAR(100) NOT NULL DEFAULT 'GOOD',
    acquired_at DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    book_copy_id UUID NOT NULL REFERENCES book_copies(id) ON DELETE RESTRICT,
    issued_at TIMESTAMPTZ NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    returned_at TIMESTAMPTZ,
    status loan_status NOT NULL,
    issued_by UUID REFERENCES users(id) ON DELETE SET NULL,
    returned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (due_at >= issued_at),
    CHECK (returned_at IS NULL OR returned_at >= issued_at)
);

CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    status reservation_status NOT NULL DEFAULT 'WAITING',
    position INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(300) NOT NULL,
    author VARCHAR(250),
    isbn VARCHAR(20),
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    justification TEXT NOT NULL,
    reason suggestion_reason NOT NULL,
    status suggestion_status NOT NULL DEFAULT 'SUBMITTED',
    submitted_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE suggestion_votes (
    suggestion_id UUID NOT NULL REFERENCES suggestions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (suggestion_id, user_id)
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE fines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL UNIQUE REFERENCES loans(id) ON DELETE CASCADE,
    overdue_days INTEGER NOT NULL DEFAULT 0 CHECK (overdue_days >= 0),
    amount NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    status fine_status NOT NULL DEFAULT 'NO_FINE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_department_role ON users(department_id, role);
CREATE INDEX idx_books_category ON books(category_id);
CREATE INDEX idx_book_departments_department ON book_departments(department_id);
CREATE INDEX idx_book_copies_book_status ON book_copies(book_id, status);
CREATE INDEX idx_loans_user_issued ON loans(user_id, issued_at);
CREATE INDEX idx_loans_copy_status ON loans(book_copy_id, status);
CREATE INDEX idx_loans_due_status ON loans(due_at, status);
CREATE INDEX idx_suggestions_department_user ON suggestions(submitted_by, created_at);
CREATE INDEX idx_suggestions_category_status ON suggestions(category_id, status);
CREATE INDEX idx_suggestions_created ON suggestions(created_at DESC);
CREATE INDEX idx_votes_suggestion ON suggestion_votes(suggestion_id);

CREATE VIEW v_department_book_relevance AS
SELECT bd.department_id, bd.book_id, bd.relevance
FROM book_departments bd;
