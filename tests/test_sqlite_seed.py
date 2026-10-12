import os
import sys
import unittest
from pathlib import Path

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "sqlite-test-only-key-never-use-outside-tests"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as backend  # noqa: E402
import seed_test_db  # noqa: E402
from models import (  # noqa: E402
    AuditLog, Author, Book, BookCopy, Category, CopyStatus, Department, Fine, Loan, LoanStatus,
    Notification, Publisher, Reservation, Suggestion, SuggestionVote, User, RoleType,
)


EXPECTED_PROFILES = [
    ("Urvashi", "25EMCAD016", RoleType.STUDENT),
    ("Yashdeep", "25TECAD016", RoleType.FACULTY),
    ("Dhruv", "25DMCAD016", RoleType.DEPARTMENT),
    ("Sphere", "25LIB016", RoleType.LIBRARIAN),
]


class SQLiteSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = backend.app.app_context()
        cls.context.push()
        backend.app.config.update(TESTING=True, APP_ENV="testing", JWT_SECRET_KEY=os.environ["JWT_SECRET_KEY"])
        backend.db.create_all()
        seed_test_db.seed_all()

    @classmethod
    def tearDownClass(cls):
        backend.db.session.remove()
        backend.db.drop_all()
        cls.context.pop()

    def test_exact_four_seed_profiles_are_database_records(self):
        users = backend.db.session.query(User).all()
        self.assertEqual(len(users), 4)
        for name, identifier, role in EXPECTED_PROFILES:
            field = User.enrollment_id if role == RoleType.STUDENT else User.employee_id
            found = backend.db.session.query(User).filter_by(name=name, role=role).filter(field == identifier).all()
            self.assertEqual(len(found), 1)

    def test_catalog_has_at_least_one_hundred_distinct_published_titles(self):
        books = backend.db.session.query(Book).all()
        self.assertGreaterEqual(len(books), 100)
        self.assertEqual(len({book.title.casefold() for book in books}), len(books))
        self.assertTrue(all(book.authors and book.category_id for book in books))
        self.assertGreater(backend.db.session.query(Publisher).count(), 0)
        self.assertGreater(backend.db.session.query(Book).filter(Book.publisher_id.is_not(None)).count(), 0)
        self.assertGreater(backend.db.session.execute(backend.text("select count(*) from book_departments")).scalar(), 0)
        catalog = __import__("json").loads((Path(__file__).resolve().parents[1] / "database" / "seed" / "books_catalog.json").read_text(encoding="utf-8"))["books"]
        self.assertEqual(len(catalog), 119)
        self.assertTrue(all(item["openlibrary_work"].startswith("/works/") for item in catalog))
        work_by_title = {item["title"]: item["openlibrary_work"] for item in catalog}
        self.assertEqual(work_by_title["The C++ Programming Language"], "/works/OL53184W")
        self.assertEqual(work_by_title["Algorithms in C"], "/works/OL21426085W")
        goal = backend.db.session.query(Book).filter_by(title="The Goal").one()
        self.assertEqual(goal.subtitle, "A Process of Ongoing Improvement")
        self.assertEqual({author.name for author in goal.authors}, {"Eliyahu M. Goldratt", "Jeff Cox"})

    def test_seed_is_idempotent_across_books_and_related_records(self):
        models = (Department, Category, User, Book, BookCopy, Loan, Reservation,
                  Suggestion, SuggestionVote, Notification, Fine, AuditLog)
        before = tuple(backend.db.session.query(model).count() for model in models)
        seed_test_db.seed_all()
        after = tuple(backend.db.session.query(model).count() for model in models)
        self.assertEqual(after, before)

    def test_sqlite_enforces_foreign_keys(self):
        self.assertEqual(backend.db.session.execute(backend.text("PRAGMA foreign_keys")).scalar(), 1)

    def test_seeded_profiles_login_and_restore_database_sessions(self):
        client = backend.app.test_client()
        for name, identifier, role in EXPECTED_PROFILES:
            with self.subTest(role=role.value):
                response = client.post("/api/auth/login", json={
                    "name": name, "user_id": identifier,
                    "role": "Teacher" if role == RoleType.FACULTY else role.value,
                })
                self.assertEqual(response.status_code, 200, response.get_json())
                token = response.get_json()["data"]["access_token"]
                restored = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(restored.status_code, 200)
                self.assertEqual(restored.get_json()["data"]["role"], role.value)

    def test_passwordless_login_is_testing_only_and_checks_exact_profile(self):
        client = backend.app.test_client()
        bad = client.post("/api/auth/login", json={
            "name": "Wrong Name", "user_id": "25EMCAD016", "role": "STUDENT"
        })
        self.assertEqual(bad.status_code, 401)
        role_mismatch = client.post("/api/auth/login", json={
            "name": "Urvashi", "user_id": "25EMCAD016", "role": "FACULTY"
        })
        self.assertEqual(role_mismatch.status_code, 401)
        with backend.app.test_request_context():
            original_env = backend.app.config.get("APP_ENV")
            backend.app.config["APP_ENV"] = "production"
            try:
                disabled = client.post("/api/auth/login", json={
                    "name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"
                })
            finally:
                backend.app.config["APP_ENV"] = original_env
        self.assertNotEqual(disabled.status_code, 200)

    def test_department_dashboard_aggregates_real_seed_rows_and_is_scoped(self):
        client = backend.app.test_client()
        login = client.post("/api/auth/login", json={
            "name": "Dhruv", "user_id": "25DMCAD016", "role": "DEPARTMENT"
        })
        self.assertEqual(login.status_code, 200, login.get_json())
        token = login.get_json()["data"]["access_token"]
        cse = backend.db.session.query(Department).filter_by(code="CSE").one()
        other_department = backend.db.session.query(Department).filter_by(code="AIDS").one()
        response = client.get(
            f"/api/reports/department/dashboard?start_date=2026-01-01&end_date=2027-01-01&department_id={other_department.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["scope"]["id"], str(cse.id))
        self.assertNotEqual(data["scope"]["id"], str(other_department.id))
        self.assertEqual(data["scope"]["name"], "Computer Science & Engineering")
        expected_books = backend.db.session.query(Book).join(Book.departments).filter(Department.id == cse.id).count()
        scoped_copies = backend.db.session.query(BookCopy).join(Book).join(Book.departments).filter(Department.id == cse.id)
        self.assertEqual(data["summary"]["department_books"], expected_books)
        self.assertEqual(data["summary"]["available_copies"], scoped_copies.filter(BookCopy.status == CopyStatus.AVAILABLE).count())
        self.assertGreater(data["summary"]["currently_borrowed"], 0)
        self.assertGreater(data["summary"]["overdue_books"], 0)
        self.assertTrue(data["charts"]["monthly_borrowing_trend"])
        self.assertTrue(data["charts"]["borrowing_by_category"])
        self.assertTrue(data["charts"]["book_copy_status"])
        self.assertTrue(data["rankings"]["top_borrowed_books"])
        self.assertTrue(data["rankings"]["top_suggested_books"])
        self.assertTrue(data["recent_suggestions"])

    def test_librarian_dashboard_returns_database_counts_only_to_librarians(self):
        client = backend.app.test_client()
        librarian_login = client.post("/api/auth/login", json={
            "name": "Sphere", "user_id": "25LIB016", "role": "LIBRARIAN"
        })
        self.assertEqual(librarian_login.status_code, 200)
        librarian_token = librarian_login.get_json()["data"]["access_token"]
        response = client.get("/api/reports/librarian/dashboard", headers={
            "Authorization": f"Bearer {librarian_token}"
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        summary = response.get_json()["data"]["summary"]
        self.assertEqual(summary["total_books"], backend.db.session.query(Book).count())
        self.assertEqual(summary["total_copies"], backend.db.session.query(BookCopy).count())
        self.assertEqual(summary["available_copies"], backend.db.session.query(BookCopy).filter_by(status=CopyStatus.AVAILABLE).count())
        self.assertEqual(summary["borrowed_copies"], backend.db.session.query(BookCopy).filter_by(status=CopyStatus.BORROWED).count())
        self.assertEqual(summary["overdue_loans"], backend.db.session.query(Loan).filter_by(status=LoanStatus.OVERDUE).count())
        self.assertEqual(summary["suggestion_votes"], backend.db.session.query(SuggestionVote).count())
        student_login = client.post("/api/auth/login", json={
            "name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"
        })
        student_token = student_login.get_json()["data"]["access_token"]
        forbidden = client.get("/api/reports/librarian/dashboard", headers={
            "Authorization": f"Bearer {student_token}"
        })
        self.assertEqual(forbidden.status_code, 403)

    def test_seed_contains_required_workflow_entities_and_statuses(self):
        self.assertGreater(backend.db.session.query(BookCopy).count(), 100)
        self.assertGreater(backend.db.session.query(Loan).count(), 0)
        self.assertGreater(backend.db.session.query(Reservation).count(), 0)
        self.assertGreater(backend.db.session.query(Suggestion).count(), 0)
        self.assertGreater(backend.db.session.query(SuggestionVote).count(), 0)
        self.assertGreater(backend.db.session.query(Notification).count(), 0)
        self.assertGreater(backend.db.session.query(Fine).count(), 0)
        self.assertGreater(backend.db.session.query(AuditLog).count(), 0)
        statuses = {row[0] for row in backend.db.session.query(Loan.status).all()}
        self.assertTrue({LoanStatus.REQUESTED, LoanStatus.APPROVED, LoanStatus.BORROWED,
                         LoanStatus.RETURNED, LoanStatus.OVERDUE}.issubset(statuses))


if __name__ == "__main__":
    unittest.main()
