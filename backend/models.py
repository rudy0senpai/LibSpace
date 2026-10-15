import enum
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Text, Integer, Boolean, Date, DateTime, ForeignKey, Enum, CheckConstraint, UniqueConstraint, func, Index, JSON, Table, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR
import uuid

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        return uuid.UUID(value)


# Association tables
book_authors = Table(
    'book_authors',
    db.metadata,
    Column('book_id', GUID, ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    Column('author_id', GUID, ForeignKey('authors.id', ondelete='CASCADE'), primary_key=True)
)

book_departments = Table(
    'book_departments',
    db.metadata,
    Column('book_id', GUID, ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    Column('department_id', GUID, ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
    Column('relevance', Integer, nullable=False, default=1),
    CheckConstraint('relevance BETWEEN 1 AND 5', name='check_relevance'),
    Index('idx_book_departments_department', 'department_id')
)


class RoleType(enum.Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    DEPARTMENT = "DEPARTMENT"
    LIBRARIAN = "LIBRARIAN"
    ADMIN = "ADMIN"


class CopyStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    BORROWED = "BORROWED"
    RESERVED = "RESERVED"
    LOST = "LOST"
    DAMAGED = "DAMAGED"
    MAINTENANCE = "MAINTENANCE"
    WITHDRAWN = "WITHDRAWN"


class LoanStatus(enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"
    LOST = "LOST"
    DAMAGED = "DAMAGED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class ReservationStatus(enum.Enum):
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class SuggestionStatus(enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    ORDERED = "ORDERED"
    AVAILABLE = "AVAILABLE"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    ALREADY_AVAILABLE = "ALREADY_AVAILABLE"


class SuggestionReason(enum.Enum):
    COURSE_REQUIREMENT = "COURSE_REQUIREMENT"
    COMPETITIVE_EXAM = "COMPETITIVE_EXAM"
    RESEARCH = "RESEARCH"
    PROGRAMMING = "PROGRAMMING"
    PERSONAL_LEARNING = "PERSONAL_LEARNING"
    FACULTY_RECOMMENDATION = "FACULTY_RECOMMENDATION"
    OTHER = "OTHER"


class FineStatus(enum.Enum):
    NO_FINE = "NO_FINE"
    PENDING = "PENDING"
    WAIVED = "WAIVED"
    PAID = "PAID"


class NotificationType(enum.Enum):
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"
    RESERVATION_AVAILABLE = "RESERVATION_AVAILABLE"
    SUGGESTION_STATUS_CHANGED = "SUGGESTION_STATUS_CHANGED"
    NEW_BOOK = "NEW_BOOK"
    SYSTEM = "SYSTEM"


class Department(db.Model):
    __tablename__ = "departments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(150), nullable=False, unique=True)
    short_name = Column(String(80), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    users = relationship("User", back_populates="department")
    books = relationship("Book", secondary=book_departments, back_populates="departments")


class User(db.Model):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Enum(RoleType, name="role_type", native_enum=True), nullable=False)
    department_id = Column(GUID, ForeignKey("departments.id", ondelete="SET NULL"))
    enrollment_id = Column(String(50))
    employee_id = Column(String(50))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    department = relationship("Department", back_populates="users")
    loans = relationship("Loan", back_populates="user", foreign_keys="Loan.user_id")
    issued_loans = relationship("Loan", back_populates="issued_by_user", foreign_keys="Loan.issued_by")
    returned_loans = relationship("Loan", back_populates="returned_to_user", foreign_keys="Loan.returned_to")
    reservations = relationship("Reservation", back_populates="user")
    suggestions = relationship("Suggestion", back_populates="submitted_by_user", foreign_keys="Suggestion.submitted_by")
    reviewed_suggestions = relationship("Suggestion", back_populates="reviewed_by_user", foreign_keys="Suggestion.reviewed_by")
    votes = relationship("SuggestionVote", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

    __table_args__ = (
        CheckConstraint(
            "((role IN ('STUDENT','FACULTY','DEPARTMENT') AND department_id IS NOT NULL) OR role IN ('LIBRARIAN','ADMIN'))",
            name="check_user_department_role"
        ),
        Index("idx_users_department_role", "department_id", "role"),
    )


class Publisher(db.Model):
    __tablename__ = "publishers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    website = Column(String(500))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class Category(db.Model):
    __tablename__ = "categories"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class Author(db.Model):
    __tablename__ = "authors"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(180), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    books = relationship("Book", secondary=book_authors, back_populates="authors")


class Book(db.Model):
    __tablename__ = "books"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    isbn = Column(String(20), unique=True)
    title = Column(String(300), nullable=False)
    subtitle = Column(String(300))
    description = Column(Text)
    publication_year = Column(Integer)
    edition = Column(String(80))
    language = Column(String(80), nullable=False, default="English")
    cover_image_ref = Column(String(500))
    publisher_id = Column(GUID, ForeignKey("publishers.id", ondelete="SET NULL"))
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    publisher = relationship("Publisher")
    category = relationship("Category")
    authors = relationship("Author", secondary=book_authors, back_populates="books")
    departments = relationship("Department", secondary=book_departments, back_populates="books")
    copies = relationship("BookCopy", back_populates="book")
    reservations = relationship("Reservation", back_populates="book")

    __table_args__ = (
        CheckConstraint("publication_year BETWEEN 1400 AND 2100", name="check_publication_year"),
        Index("idx_books_category", "category_id"),
    )


class BookCopy(db.Model):
    __tablename__ = "book_copies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    book_id = Column(GUID, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    accession_number = Column(String(50), nullable=False, unique=True)
    barcode = Column(String(100), nullable=False, unique=True)
    rack = Column(String(80), nullable=False)
    shelf = Column(String(80), nullable=False)
    status = Column(Enum(CopyStatus, name="copy_status", native_enum=True), nullable=False, default=CopyStatus.AVAILABLE)
    condition = Column(String(100), nullable=False, default="GOOD")
    acquired_at = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    book = relationship("Book", back_populates="copies")
    loans = relationship("Loan", back_populates="book_copy")

    __table_args__ = (
        Index("idx_book_copies_book_status", "book_id", "status"),
    )


class Loan(db.Model):
    __tablename__ = "loans"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    book_copy_id = Column(GUID, ForeignKey("book_copies.id", ondelete="RESTRICT"), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=False)
    returned_at = Column(DateTime(timezone=True))
    status = Column(Enum(LoanStatus, name="loan_status", native_enum=True), nullable=False)
    issued_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"))
    returned_to = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="loans", foreign_keys=[user_id])
    book_copy = relationship("BookCopy", back_populates="loans")
    issued_by_user = relationship("User", back_populates="issued_loans", foreign_keys=[issued_by])
    returned_to_user = relationship("User", back_populates="returned_loans", foreign_keys=[returned_to])
    fine = relationship("Fine", back_populates="loan", uselist=False)

    __table_args__ = (
        CheckConstraint("due_at >= issued_at", name="check_due_after_issued"),
        CheckConstraint("returned_at IS NULL OR returned_at >= issued_at", name="check_return_after_issued"),
        Index("idx_loans_user_issued", "user_id", "issued_at"),
        Index("idx_loans_copy_status", "book_copy_id", "status"),
        Index("idx_loans_due_status", "due_at", "status"),
        Index(
            "uq_loans_one_active_request_per_copy", "book_copy_id", unique=True,
            sqlite_where=text("status IN ('REQUESTED','APPROVED','BORROWED','OVERDUE')"),
            postgresql_where=text("status IN ('REQUESTED','APPROVED','BORROWED','OVERDUE')"),
        ),
    )


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(GUID, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ReservationStatus, name="reservation_status", native_enum=True), nullable=False, default=ReservationStatus.WAITING)
    position = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")

    __table_args__ = (
        Index("idx_reservations_user_status", "user_id", "status"),
    )


class Suggestion(db.Model):
    __tablename__ = "suggestions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    author = Column(String(250))
    isbn = Column(String(20))
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="SET NULL"))
    justification = Column(Text, nullable=False)
    reason = Column(Enum(SuggestionReason, name="suggestion_reason", native_enum=True), nullable=False)
    status = Column(Enum(SuggestionStatus, name="suggestion_status", native_enum=True), nullable=False, default=SuggestionStatus.SUBMITTED)
    submitted_by = Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    category = relationship("Category")
    submitted_by_user = relationship("User", back_populates="suggestions", foreign_keys=[submitted_by])
    reviewed_by_user = relationship("User", back_populates="reviewed_suggestions", foreign_keys=[reviewed_by])
    votes = relationship("SuggestionVote", back_populates="suggestion", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_suggestions_department_user", "submitted_by", "created_at"),
        Index("idx_suggestions_category_status", "category_id", "status"),
        Index("idx_suggestions_created", "created_at"),
    )


class SuggestionVote(db.Model):
    __tablename__ = "suggestion_votes"

    suggestion_id = Column(GUID, ForeignKey("suggestions.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    suggestion = relationship("Suggestion", back_populates="votes")
    user = relationship("User", back_populates="votes")

    __table_args__ = (
        Index("idx_votes_suggestion", "suggestion_id"),
    )


class Notification(db.Model):
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(NotificationType, name="notification_type", native_enum=True), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    user = relationship("User", back_populates="notifications")


class Fine(db.Model):
    __tablename__ = "fines"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    loan_id = Column(GUID, ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, unique=True)
    overdue_days = Column(Integer, nullable=False, default=0)
    amount = Column(db.Numeric(10, 2), nullable=False, default=0)
    status = Column(Enum(FineStatus, name="fine_status", native_enum=True), nullable=False, default=FineStatus.NO_FINE)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    loan = relationship("Loan", back_populates="fine")

    __table_args__ = (
        CheckConstraint("overdue_days >= 0", name="check_overdue_days"),
        CheckConstraint("amount >= 0", name="check_amount"),
    )


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(GUID)
    details = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())