import os
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

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

    def test_seed_has_exact_required_role_counts_and_department_accounts(self):
        counts = {
            role.value: backend.db.session.query(User).filter_by(role=role).count()
            for role in (RoleType.STUDENT, RoleType.FACULTY, RoleType.DEPARTMENT, RoleType.LIBRARIAN)
        }
        self.assertEqual(counts, {"STUDENT": 100, "FACULTY": 30, "DEPARTMENT": 9, "LIBRARIAN": 2})
        departments = {department.name: department for department in backend.db.session.query(Department).all()}
        expected = {
            "B.Tech - CSE": "25DMCAD016", "B.Tech - AI&DS": "DEPT-AIDS",
            "B.Tech - AI&ML": "DEPT-AIML", "B.Tech - Mechanical": "DEPT-MECH",
            "B.Tech - Electrical": "DEPT-ELEC", "B.Tech - Civil": "DEPT-CIVIL",
            "BBA": "DEPT-BBA", "BCA": "DEPT-BCA", "M.Tech": "DEPT-MTECH",
        }
        self.assertTrue(set(expected).issubset(departments))
        for department_name, identifier in expected.items():
            with self.subTest(department=department_name):
                account = backend.db.session.query(User).filter_by(role=RoleType.DEPARTMENT, employee_id=identifier).one()
                self.assertEqual(account.department_id, departments[department_name].id)

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

    def _login_token(self, name, user_id, role):
        response = backend.app.test_client().post("/api/auth/login", json={
            "name": name, "user_id": user_id, "role": role,
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["data"]["access_token"]

    def _available_unrequested_book(self):
        for book in backend.db.session.query(Book).order_by(Book.title).all():
            copy = backend.db.session.query(BookCopy).filter_by(
                book_id=book.id, status=CopyStatus.AVAILABLE
            ).first()
            if copy and backend.db.session.query(Loan).filter(
                Loan.book_copy_id == copy.id,
                Loan.status.in_((LoanStatus.REQUESTED, LoanStatus.APPROVED, LoanStatus.BORROWED, LoanStatus.OVERDUE)),
            ).count() == 0:
                return book
        self.fail("No available unrequested test copy found")

    def test_student_request_is_persisted_reviewed_issued_and_user_scoped(self):
        client = backend.app.test_client()
        student_token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        book = self._available_unrequested_book()
        response = client.post("/api/users/me/loans/requests", json={"book_id": str(book.id)},
                               headers={"Authorization": f"Bearer {student_token}"})
        self.assertEqual(response.status_code, 201, response.get_json())
        loan_id = response.get_json()["data"]["id"]
        loan = backend.db.session.get(Loan, loan_id)
        self.assertEqual(loan.status, LoanStatus.REQUESTED)
        self.assertEqual(loan.book_copy.status, CopyStatus.RESERVED)

        own_loans = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {student_token}"})
        self.assertIn(loan_id, {row["id"] for row in own_loans.get_json()["data"]})
        other_token = self._login_token("Student Demo 001", "STD-DEMO-001", "STUDENT")
        other_loans = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {other_token}"})
        self.assertNotIn(loan_id, {row["id"] for row in other_loans.get_json()["data"]})

        forbidden = client.post(f"/api/librarian/loan-requests/{loan_id}/review", json={"decision": "APPROVED"},
                                headers={"Authorization": f"Bearer {student_token}"})
        self.assertEqual(forbidden.status_code, 403)
        librarian_token = self._login_token("Sphere", "25LIB016", "LIBRARIAN")
        queue = client.get("/api/librarian/loan-requests", headers={"Authorization": f"Bearer {librarian_token}"})
        self.assertIn(loan_id, {row["id"] for row in queue.get_json()["data"]})
        reviewed = client.post(f"/api/librarian/loan-requests/{loan_id}/review", json={"decision": "APPROVED"},
                               headers={"Authorization": f"Bearer {librarian_token}"})
        self.assertEqual(reviewed.status_code, 200, reviewed.get_json())
        self.assertEqual(backend.db.session.get(Loan, loan_id).status, LoanStatus.APPROVED)
        issued = client.post(f"/api/librarian/loan-requests/{loan_id}/issue", json={},
                             headers={"Authorization": f"Bearer {librarian_token}"})
        self.assertEqual(issued.status_code, 200, issued.get_json())
        backend.db.session.expire_all()
        persisted = backend.db.session.get(Loan, loan_id)
        self.assertEqual(persisted.status, LoanStatus.BORROWED)
        self.assertEqual(persisted.book_copy.status, CopyStatus.BORROWED)
        self.assertIsNotNone(persisted.due_at)

    def test_librarian_rejection_releases_reserved_copy_and_duplicate_request_is_blocked(self):
        client = backend.app.test_client()
        student_token = self._login_token("Yashdeep", "25TECAD016", "FACULTY")
        book = self._available_unrequested_book()
        headers = {"Authorization": f"Bearer {student_token}"}
        first = client.post("/api/users/me/loans/requests", json={"book_id": str(book.id)}, headers=headers)
        self.assertEqual(first.status_code, 201, first.get_json())
        duplicate = client.post("/api/users/me/loans/requests", json={"book_id": str(book.id)}, headers=headers)
        self.assertEqual(duplicate.status_code, 409)
        loan_id = first.get_json()["data"]["id"]
        librarian_token = self._login_token("Sphere", "25LIB016", "LIBRARIAN")
        rejected = client.post(f"/api/librarian/loan-requests/{loan_id}/review", json={"decision": "REJECTED"},
                               headers={"Authorization": f"Bearer {librarian_token}"})
        self.assertEqual(rejected.status_code, 200, rejected.get_json())
        backend.db.session.expire_all()
        loan = backend.db.session.get(Loan, loan_id)
        self.assertEqual(loan.status, LoanStatus.REJECTED)
        self.assertEqual(loan.book_copy.status, CopyStatus.AVAILABLE)

    def test_partial_unique_index_prevents_two_active_requests_for_one_copy(self):
        book = self._available_unrequested_book()
        copy = backend.db.session.query(BookCopy).filter_by(
            book_id=book.id, status=CopyStatus.AVAILABLE
        ).first()
        first_user = backend.db.session.query(User).filter_by(enrollment_id="25EMCAD016").one()
        second_user = backend.db.session.query(User).filter_by(employee_id="25TECAD016").one()
        now = datetime.now()
        first = Loan(
            user_id=first_user.id, book_copy_id=copy.id, issued_at=now,
            due_at=now + timedelta(days=14), status=LoanStatus.REQUESTED,
        )
        backend.db.session.add(first)
        backend.db.session.flush()
        second = Loan(
            user_id=second_user.id, book_copy_id=copy.id, issued_at=now,
            due_at=now + timedelta(days=14), status=LoanStatus.REQUESTED,
        )
        backend.db.session.add(second)
        with self.assertRaises(IntegrityError):
            backend.db.session.flush()
        backend.db.session.rollback()

    def test_book_search_paginates_filters_and_rejects_invalid_pagination(self):
        client = backend.app.test_client()
        token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        headers = {"Authorization": f"Bearer {token}"}
        page_one = client.get("/api/books/search?page=1&per_page=10", headers=headers)
        self.assertEqual(page_one.status_code, 200, page_one.get_json())
        self.assertEqual(len(page_one.get_json()["data"]["items"]), 10)
        self.assertEqual(page_one.get_json()["data"]["total"], 119)
        page_two = client.get("/api/books/search?page=2&per_page=10", headers=headers)
        self.assertEqual(page_two.status_code, 200)
        self.assertNotEqual(page_one.get_json()["data"]["items"][0]["id"], page_two.get_json()["data"]["items"][0]["id"])
        available = client.get("/api/books/search?availability=available&per_page=100", headers=headers)
        self.assertEqual(available.status_code, 200)
        self.assertTrue(all(book["available"] > 0 for book in available.get_json()["data"]["items"]))
        self.assertEqual(client.get("/api/books/search?page=0", headers=headers).status_code, 400)
        self.assertEqual(client.get("/api/books/search?per_page=101", headers=headers).status_code, 400)

    def test_suggestion_vote_state_is_persistent_and_repeated_vote_is_idempotent(self):
        client = backend.app.test_client()
        first_token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        second_token = self._login_token("Yashdeep", "25TECAD016", "FACULTY")
        first_headers = {"Authorization": f"Bearer {first_token}"}
        second_headers = {"Authorization": f"Bearer {second_token}"}
        created = client.post("/api/suggestions", json={
            "title": "Test voting state book", "justification": "Automated test fixture",
            "reason": "COURSE_REQUIREMENT",
        }, headers=first_headers)
        self.assertEqual(created.status_code, 201, created.get_json())
        suggestion_id = created.get_json()["data"]["id"]

        initial = client.get("/api/users/me/suggestions", headers=first_headers).get_json()["data"]
        self.assertFalse(next(item for item in initial if item["id"] == suggestion_id)["voted_by_me"])
        first_vote = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=first_headers)
        second_vote = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=first_headers)
        self.assertEqual(first_vote.status_code, 200)
        self.assertEqual(second_vote.get_json()["data"], {"voted": True, "vote_count": 1})
        persisted = client.get("/api/users/me/suggestions", headers=first_headers).get_json()["data"]
        self.assertTrue(next(item for item in persisted if item["id"] == suggestion_id)["voted_by_me"])
        other_user = client.get("/api/users/me/suggestions", headers=second_headers).get_json()["data"]
        self.assertFalse(next(item for item in other_user if item["id"] == suggestion_id)["voted_by_me"])

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

    def test_testing_login_casefolds_and_trims_identity_without_rewriting_display_name(self):
        client = backend.app.test_client()
        response = client.post("/api/auth/login", json={
            "name": "  dHRUV ", "user_id": " 25dmCAD016 ", "role": " department "
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["data"]["user"]["name"], "Dhruv")
        internal_space = client.post("/api/auth/login", json={
            "name": "Dhruv", "user_id": "25dm cad016", "role": "DEPARTMENT"
        })
        self.assertEqual(internal_space.status_code, 401)

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
        self.assertEqual(data["scope"]["name"], "B.Tech - CSE")
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
        self.assertTrue(data["categories"])
        category_id = data["categories"][0]["category_id"]
        filtered = client.get(
            f"/api/reports/department/dashboard?start_date=2026-01-01&end_date=2027-01-01&category_id={category_id}&user_type=STUDENT&suggestion_status=APPROVED",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(filtered.status_code, 200, filtered.get_json())
        filtered_data = filtered.get_json()["data"]
        self.assertLessEqual(filtered_data["summary"]["department_books"], data["summary"]["department_books"])
        self.assertEqual(filtered_data["summary"]["active_faculty"], 0)
        self.assertTrue(all(row["category_name"] == data["categories"][0]["category_name"]
                            for row in filtered_data["borrowing_by_category"]))
        self.assertTrue(all(row["status"] == "APPROVED" for row in filtered_data["suggestions"]["items"]))
        invalid_filter = client.get(
            "/api/reports/department/dashboard?category_id=not-a-category",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(invalid_filter.status_code, 422)

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
