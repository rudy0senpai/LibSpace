"""Create/update the isolated SQLite demo database; never connects to PostgreSQL."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BACKEND_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true",
        help="Explicitly remove only the configured SQLite test DB before creating it.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.environ["APP_ENV"] = "testing"
    # Deliberately ignore DATABASE_URL (which may point to PostgreSQL). A separate
    # TEST_DATABASE_URL override is accepted only for SQLite URLs.
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite:///libsphere_test.db")
    if not database_url.startswith("sqlite:"):
        raise SystemExit("TEST_DATABASE_URL must be a SQLite URL; PostgreSQL is never used by this script.")
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(32))
else:
    args = argparse.Namespace(reset=False)

sys.path.insert(0, str(BACKEND_DIR))
from sqlalchemy.engine import make_url  # noqa: E402
from app import app, db  # noqa: E402
from models import (  # noqa: E402
    AuditLog, Author, Book, BookCopy, Category, CopyStatus, Department, Fine, FineStatus,
    Loan, LoanStatus, Notification, NotificationType, Publisher, Reservation,
    ReservationStatus, Suggestion, SuggestionReason, SuggestionStatus,
    SuggestionVote, User, RoleType,
)

DATABASE_URL = app.config.get("SQLALCHEMY_DATABASE_URI")
if not DATABASE_URL or not DATABASE_URL.startswith("sqlite:"):
    raise SystemExit("Refusing to use a non-SQLite database for test seeding.")
url = make_url(DATABASE_URL)
if url.database in (None, "", ":memory:"):
    db_file = None
else:
    configured_path = Path(url.database)
    db_file = configured_path if configured_path.is_absolute() else INSTANCE_DIR / configured_path
    db_file = db_file.resolve()
    try:
        db_file.relative_to(INSTANCE_DIR.resolve())
    except ValueError as exc:
        raise SystemExit("SQLite test database must be located under backend/instance/.") from exc

if args.reset and db_file:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_file) + suffix)
        if candidate.exists():
            candidate.unlink()


CATALOG_PATH = BACKEND_DIR.parent / "database" / "seed" / "books_catalog.json"
NAMESPACE = uuid.UUID("d729176f-b18c-4c9c-b095-27eb904277cc")
PROFILES = [
    {"name": "Urvashi", "user_id": "25EMCAD016", "role": RoleType.STUDENT,
     "email": "urvashi@libsphere.test", "department": "CSE", "identifier": "enrollment_id"},
    {"name": "Yashdeep", "user_id": "25TECAD016", "role": RoleType.FACULTY,
     "email": "yashdeep@libsphere.test", "department": "CSE", "identifier": "employee_id"},
    {"name": "Dhruv", "user_id": "25DMCAD016", "role": RoleType.DEPARTMENT,
     "email": "dhruv@libsphere.test", "department": "CSE", "identifier": "employee_id"},
    {"name": "Sphere", "user_id": "25LIB016", "role": RoleType.LIBRARIAN,
     "email": "sphere@libsphere.test", "department": None, "identifier": "employee_id"},
]
DEPARTMENTS = [
    ("CSE", "Computer Science & Engineering", "CSE"),
    ("AIDS", "Artificial Intelligence & Data Science", "AI&DS"),
    ("ECE", "Electronics & Communication Engineering", "ECE"),
    ("ME", "Mechanical Engineering", "ME"),
    ("CE", "Civil Engineering", "Civil"),
    ("EE", "Electrical Engineering", "EE"),
    ("MBA", "Master of Business Administration", "MBA"),
]
PUBLISHERS = [
    "Addison-Wesley", "Cambridge University Press", "Cengage", "Dorset House",
    "Farrar, Straus and Giroux", "Harper Business", "HarperCollins", "Harvard Business Review Press",
    "IT Revolution", "McGraw-Hill", "Microsoft Press", "MIT Press", "Morgan Kaufmann", "No Starch Press",
    "O'Reilly Media", "Pearson", "Penguin Books", "Portfolio", "Pragmatic Bookshelf",
    "Prentice Hall", "Springer", "Wiley", "Wellesley-Cambridge Press", "Avery", "Crown Business",
    "Doubleday", "Grand Central Publishing", "Simon & Schuster", "North River Press",
]
# Original/known publishers are assigned only for works with well-established imprint data.
PUBLISHER_BY_TITLE = {
    "Clean Code": "Prentice Hall", "The Pragmatic Programmer": "Addison-Wesley",
    "Code Complete": "Microsoft Press", "Design Patterns": "Addison-Wesley",
    "The Mythical Man-Month": "Addison-Wesley", "Clean Architecture": "Pearson",
    "Software Engineering at Google": "O'Reilly Media", "Domain-Driven Design": "Addison-Wesley",
    "Head First Design Patterns": "O'Reilly Media", "Release It!": "Pragmatic Bookshelf",
    "Peopleware": "Dorset House", "The DevOps Handbook": "IT Revolution",
    "The Phoenix Project": "IT Revolution", "Continuous Delivery": "Addison-Wesley",
    "Effective Java": "Addison-Wesley", "The C Programming Language": "Prentice Hall",
    "Fluent Python": "O'Reilly Media", "Python Crash Course": "No Starch Press",
    "Learning Python": "O'Reilly Media", "Think Python": "O'Reilly Media",
    "Automate the Boring Stuff with Python": "No Starch Press", "Eloquent JavaScript": "No Starch Press",
    "Java Concurrency in Practice": "Addison-Wesley", "Introduction to Algorithms": "MIT Press",
    "Algorithms": "Addison-Wesley", "Data Structures and Algorithms in Python": "Wiley",
    "Database System Concepts": "McGraw-Hill", "Fundamentals of Database Systems": "Pearson",
    "Database Internals": "O'Reilly Media", "Designing Data-Intensive Applications": "O'Reilly Media",
    "SQL Antipatterns": "Pragmatic Bookshelf", "Learning SQL": "O'Reilly Media",
    "The Data Warehouse Toolkit": "Wiley", "Operating System Concepts": "Wiley",
    "Modern Operating Systems": "Pearson", "Computer Networking: A Top-Down Approach": "Pearson",
    "Computer Networks": "Pearson", "TCP/IP Illustrated": "Addison-Wesley",
    "Data and Computer Communications": "Pearson", "Deep Learning": "MIT Press",
    "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow": "O'Reilly Media",
    "Pattern Recognition and Machine Learning": "Springer",
    "The Elements of Statistical Learning": "Springer", "Python for Data Analysis": "O'Reilly Media",
    "R for Data Science": "O'Reilly Media", "The Lean Startup": "Crown Business",
    "The Innovator's Dilemma": "Harvard Business Review Press", "Good to Great": "HarperCollins",
    "The Fifth Discipline": "Doubleday", "Measure What Matters": "Portfolio",
    "Thinking, Fast and Slow": "Farrar, Straus and Giroux", "Deep Work": "Grand Central Publishing",
    "Getting Things Done": "Penguin Books", "Atomic Habits": "Avery",
    "The Effective Executive": "Harper Business", "The Personal MBA": "Portfolio",
    "The Hard Thing About Hard Things": "Harper Business", "The Goal": "North River Press",
}


def stable_id(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


def by_name(model, name):
    return db.session.query(model).filter(db.func.lower(model.name) == name.casefold()).first()


def seed_all():
    with app.app_context():
        if app.config.get("APP_ENV") != "testing" or db.engine.dialect.name != "sqlite":
            raise RuntimeError("Refusing to seed outside the SQLite testing environment.")
        db.create_all()
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["books"]
        departments = {}
        for code, name, short_name in DEPARTMENTS:
            department = db.session.query(Department).filter_by(code=code).first()
            if department is None:
                department = Department(code=code, name=name, short_name=short_name)
                db.session.add(department)
            else:
                department.name, department.short_name, department.is_active = name, short_name, True
            departments[code] = department
        categories = {}
        category_names = sorted({book["category"] for book in catalog} | {"Database Systems"})
        for name in category_names:
            category = by_name(Category, name)
            if category is None:
                category = Category(name=name, description=f"Books and references in {name}.")
                db.session.add(category)
            categories[name] = category
        publishers = {}
        for name in PUBLISHERS:
            publisher = by_name(Publisher, name)
            if publisher is None:
                publisher = Publisher(name=name)
                db.session.add(publisher)
            publishers[name] = publisher
        db.session.flush()

        users = {}
        for profile in PROFILES:
            user = db.session.query(User).filter_by(email=profile["email"]).first()
            if user is None:
                user = User(
                    name=profile["name"], email=profile["email"],
                    password_hash=__import__("werkzeug.security", fromlist=["generate_password_hash"]).generate_password_hash(secrets.token_urlsafe(32)),
                    role=profile["role"],
                )
                db.session.add(user)
            user.name = profile["name"]
            user.role = profile["role"]
            user.department = departments.get(profile["department"])
            setattr(user, profile["identifier"], profile["user_id"])
            user.is_active = True
            users[profile["role"]] = user
        db.session.flush()

        librarian = users[RoleType.LIBRARIAN]
        for record in catalog:
            title = record["title"].strip()
            book = db.session.query(Book).filter(db.func.lower(Book.title) == title.casefold()).first()
            if book is None:
                book = Book(title=title)
                db.session.add(book)
            book.title = title
            book.subtitle = record.get("subtitle")
            book.isbn = None  # No ISBN is stored unless edition-level verification is available.
            book.description = None
            book.publication_year = record.get("year")
            book.edition = None
            book.language = "English"
            book.category = categories[record["category"]]
            publisher_name = PUBLISHER_BY_TITLE.get(title)
            book.publisher = publishers.get(publisher_name)
            desired_authors = []
            for author_name in record["authors"]:
                author = by_name(Author, author_name)
                if author is None:
                    author = Author(name=author_name)
                    db.session.add(author)
                    db.session.flush()
                if author not in desired_authors:
                    desired_authors.append(author)
            book.authors[:] = desired_authors
            related_departments = {"CSE"}
            if record["category"] == "AI and Machine Learning":
                related_departments.add("AIDS")
            elif record["category"] in {"Networks", "Computer Architecture", "Cybersecurity"}:
                related_departments.add("ECE")
            elif record["category"] == "Management":
                related_departments.add("MBA")
            for code in related_departments:
                if departments[code] not in book.departments:
                    book.departments.append(departments[code])
        db.session.flush()

        books = db.session.query(Book).order_by(Book.title).all()
        copies = {}
        for index, book in enumerate(books, start=1):
            for suffix in ("A", "B"):
                accession = f"DEMO-{index:03d}-{suffix}"
                copy = db.session.query(BookCopy).filter_by(accession_number=accession).first()
                if copy is None:
                    copy = BookCopy(
                        book=book, accession_number=accession, barcode=f"LIB-DEMO-{index:03d}-{suffix}",
                        rack=f"R-{(index - 1) % 12 + 1:02d}", shelf=f"S-{(index - 1) % 8 + 1:02d}",
                        status=CopyStatus.AVAILABLE, condition="GOOD", acquired_at=date(2025, 1, 15),
                    )
                    db.session.add(copy)
                copies[(book.id, suffix)] = copy
        db.session.flush()

        now = datetime.now().replace(microsecond=0)
        cse_books = [book for book in books if any(d.code == "CSE" for d in book.departments)]
        student, faculty, department_user = users[RoleType.STUDENT], users[RoleType.FACULTY], users[RoleType.DEPARTMENT]
        loan_statuses = [
            LoanStatus.RETURNED, LoanStatus.RETURNED, LoanStatus.RETURNED, LoanStatus.RETURNED,
            LoanStatus.BORROWED, LoanStatus.BORROWED, LoanStatus.OVERDUE,
            LoanStatus.REQUESTED, LoanStatus.APPROVED,
        ]
        loan_records = []
        for i, status in enumerate(loan_statuses):
            book = cse_books[i]
            copy = copies[(book.id, "A")]
            issued_at = now - timedelta(days=(8 - (i % 8)) * 31 + i)
            due_at = now - timedelta(days=7) if status == LoanStatus.OVERDUE else issued_at + timedelta(days=14)
            returned_at = issued_at + timedelta(days=12) if status == LoanStatus.RETURNED else None
            loan = db.session.query(Loan).filter_by(id=stable_id(f"loan-{i}")).first()
            if loan is None:
                loan = Loan(
                    id=stable_id(f"loan-{i}"), user=student if i % 2 == 0 else faculty,
                    book_copy=copy, issued_at=issued_at, due_at=due_at, returned_at=returned_at,
                    status=status, issued_by_user=librarian,
                    returned_to_user=librarian if returned_at else None,
                )
                db.session.add(loan)
            else:
                loan.status, loan.due_at, loan.returned_at = status, due_at, returned_at
            copy.status = CopyStatus.BORROWED if status in {LoanStatus.BORROWED, LoanStatus.OVERDUE} else (
                CopyStatus.RESERVED if status in {LoanStatus.REQUESTED, LoanStatus.APPROVED} else CopyStatus.AVAILABLE
            )
            loan_records.append(loan)
        db.session.flush()

        for i, status in enumerate((ReservationStatus.WAITING, ReservationStatus.ACTIVE, ReservationStatus.FULFILLED)):
            key = f"reservation-{i}"
            reservation = db.session.query(Reservation).filter_by(id=stable_id(key)).first()
            if reservation is None:
                db.session.add(Reservation(
                    id=stable_id(key), user=student if i != 2 else faculty,
                    book=cse_books[10 + i], status=status, position=i + 1 if status == ReservationStatus.WAITING else None,
                    expires_at=now + timedelta(days=3) if status == ReservationStatus.ACTIVE else None,
                ))

        suggestions = []
        suggestion_statuses = list(SuggestionStatus)
        for i, book in enumerate(cse_books[:12]):
            key = f"suggestion-{i}"
            suggestion = db.session.query(Suggestion).filter_by(id=stable_id(key)).first()
            if suggestion is None:
                submitter = (student, faculty, department_user)[i % 3]
                suggestion = Suggestion(
                    id=stable_id(key), title=f"{book.title} — additional reference copy",
                    author=", ".join(a.name for a in book.authors), isbn=None,
                    category=book.category, justification=f"Additional departmental learning resource: {book.title}.",
                    reason=SuggestionReason.COURSE_REQUIREMENT if i % 2 == 0 else SuggestionReason.RESEARCH,
                    status=suggestion_statuses[i % len(suggestion_statuses)], submitted_by_user=submitter,
                    created_at=now - timedelta(days=2 * i + 1),
                )
                db.session.add(suggestion)
            suggestions.append(suggestion)
        db.session.flush()
        all_users = [users[p["role"]] for p in PROFILES]
        for i, suggestion in enumerate(suggestions):
            submitter_id = suggestion.submitted_by
            for voter in all_users:
                if voter.id == submitter_id or (i + voter.id.int) % 2:
                    continue
                vote = db.session.query(SuggestionVote).filter_by(
                    suggestion_id=suggestion.id, user_id=voter.id
                ).first()
                if vote is None:
                    db.session.add(SuggestionVote(suggestion_id=suggestion.id, user_id=voter.id))

        for index, loan in enumerate(loan_records):
            if loan.status == LoanStatus.OVERDUE:
                fine = db.session.query(Fine).filter_by(loan_id=loan.id).first()
                if fine is None:
                    db.session.add(Fine(
                        id=stable_id(f"fine-{index}"), loan=loan,
                        overdue_days=7, amount=70, status=FineStatus.PENDING,
                    ))
        notification_types = list(NotificationType)
        for i, profile in enumerate(PROFILES):
            user = users[profile["role"]]
            notice_id = stable_id(f"notification-{i}")
            if db.session.get(Notification, notice_id) is None:
                db.session.add(Notification(
                    id=notice_id, user=user, type=notification_types[i],
                    title=("Local demo data ready" if i == 0 else "Library update"),
                    message="This notification is generated from the local test dataset.",
                    created_at=now - timedelta(hours=i),
                ))
        for i, action in enumerate(("CATALOG_SEEDED", "LOAN_ISSUED", "SUGGESTION_REVIEWED")):
            audit_id = stable_id(f"audit-{i}")
            if db.session.get(AuditLog, audit_id) is None:
                db.session.add(AuditLog(
                    id=audit_id, actor_user_id=librarian.id, action=action,
                    entity_type="demo", entity_id=None,
                    details={"environment": "testing", "sample": i + 1},
                ))
        db.session.commit()
        return {
            "database": str(db_file) if db_file else "in-memory SQLite",
            "books": db.session.query(Book).count(),
            "profiles": db.session.query(User).filter(User.email.like("%@libsphere.test")).count(),
            "copies": db.session.query(BookCopy).count(),
            "loans": db.session.query(Loan).count(),
        }


if __name__ == "__main__":
    print(json.dumps(seed_all(), indent=2))
