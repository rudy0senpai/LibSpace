import os
import sys
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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
        self.assertGreaterEqual(len(catalog), 100)
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

    def test_file_backed_seed_refuses_a_fresh_legacy_blank_isbn_catalogue(self):
        original_path = seed_test_db.db_file
        backend.db.drop_all()
        seed_test_db.db_file = Path("C:/fake/libsphere_test.db")
        try:
            with self.assertRaisesRegex(RuntimeError, "legacy catalog has no ISBNs"):
                seed_test_db.seed_all()
        finally:
            seed_test_db.db_file = original_path
            seed_test_db.seed_all()

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

    def test_catalog_search_finds_title_author_and_isbn_without_optional_category_or_department(self):
        marker = uuid.uuid4().hex[:10]
        author = Author(name=f"Vera Searchauthor {marker}")
        book = Book(
            title=f"Crossrole Shelf Search {marker}",
            isbn=f"979{marker}",
            authors=[author],
        )
        backend.db.session.add(book)
        backend.db.session.commit()
        try:
            client = backend.app.test_client()
            token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
            headers = {"Authorization": f"Bearer {token}"}
            for term in (book.title, author.name, book.isbn):
                with self.subTest(term=term):
                    response = client.get("/api/books/search", query_string={"q": term}, headers=headers)
                    self.assertEqual(response.status_code, 200, response.get_json())
                    data = response.get_json()["data"]
                    self.assertEqual(data["total"], 1)
                    self.assertEqual(data["items"][0]["title"], book.title)

            empty = client.get("/api/books/search", query_string={"q": f"missing-{marker}"}, headers=headers)
            self.assertEqual(empty.status_code, 200)
            self.assertEqual(empty.get_json()["data"]["items"], [])
            self.assertEqual(client.get("/api/books/search").status_code, 401)
        finally:
            backend.db.session.delete(book)
            backend.db.session.delete(author)
            backend.db.session.commit()

    def test_catalog_search_returns_local_cover_and_expanded_metadata(self):
        marker = uuid.uuid4().hex[:10]
        author = Author(name=f"Cover Card Author {marker}")
        publisher = Publisher(name=f"Cover Card Publisher {marker}")
        book = Book(
            title=f"Cover Card Record {marker}", isbn=f"978{marker}", description="Local description",
            publication_year=2021, edition="Second edition", language="English", cover_image_ref="/images/catalog-cover.jpg",
            publisher=publisher, authors=[author],
        )
        copy = BookCopy(
            book=book, accession_number=f"ACC-{marker}", barcode=f"BAR-{marker}", rack="R-4", shelf="S-2",
            acquired_at=datetime.now().date(), status=CopyStatus.AVAILABLE,
        )
        backend.db.session.add_all([book, copy])
        backend.db.session.commit()
        try:
            token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
            response = backend.app.test_client().get(
                "/api/books/search", query_string={"q": book.title},
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            result = response.get_json()["data"]["items"][0]
            self.assertEqual(result["description"], "Local description")
            self.assertEqual(result["publication_year"], 2021)
            self.assertEqual(result["publisher"], publisher.name)
            self.assertEqual(result["edition"], "Second edition")
            self.assertEqual(result["language"], "English")
            self.assertEqual(result["cover_image_ref"], "/images/catalog-cover.jpg")
            self.assertEqual(result["shelf"], "S-2")
        finally:
            backend.db.session.delete(copy)
            backend.db.session.delete(book)
            backend.db.session.delete(author)
            backend.db.session.delete(publisher)
            backend.db.session.commit()

    def test_catalog_search_rejects_overlong_query(self):
        client = backend.app.test_client()
        token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        response = client.get("/api/books/search", query_string={"q": "x" * 201},
                              headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_FILTER")

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

    def test_suggestion_vote_can_toggle_off_and_on_and_is_scoped_to_authenticated_user(self):
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
        try:
            first_vote = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=first_headers,
                                     json={"user_id": str(backend.db.session.query(User).filter_by(name="Yashdeep").one().id)})
            self.assertEqual(first_vote.status_code, 200)
            self.assertEqual(first_vote.get_json()["data"], {"voted": True, "vote_count": 1})
            self.assertEqual(backend.db.session.query(SuggestionVote).filter_by(suggestion_id=suggestion_id).one().user_id,
                             backend.db.session.query(User).filter_by(name="Urvashi").one().id)

            unvote = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=first_headers)
            self.assertEqual(unvote.status_code, 200)
            self.assertEqual(unvote.get_json()["data"], {"voted": False, "vote_count": 0})
            after_refresh = client.get("/api/users/me/suggestions", headers=first_headers).get_json()["data"]
            self.assertFalse(next(item for item in after_refresh if item["id"] == suggestion_id)["voted_by_me"])

            again = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=first_headers)
            self.assertEqual(again.get_json()["data"], {"voted": True, "vote_count": 1})
            other_user = client.get("/api/users/me/suggestions", headers=second_headers).get_json()["data"]
            self.assertFalse(next(item for item in other_user if item["id"] == suggestion_id)["voted_by_me"])
            other_vote = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=second_headers)
            self.assertEqual(other_vote.get_json()["data"], {"voted": True, "vote_count": 2})
            persisted_first = client.get("/api/users/me/suggestions", headers=first_headers).get_json()["data"]
            persisted_second = client.get("/api/users/me/suggestions", headers=second_headers).get_json()["data"]
            self.assertTrue(next(item for item in persisted_first if item["id"] == suggestion_id)["voted_by_me"])
            self.assertTrue(next(item for item in persisted_second if item["id"] == suggestion_id)["voted_by_me"])
            self.assertEqual(backend.db.session.query(SuggestionVote).filter_by(suggestion_id=suggestion_id).count(), 2)
        finally:
            backend.db.session.query(Suggestion).filter_by(id=suggestion_id).delete(synchronize_session=False)
            backend.db.session.commit()

    def test_vote_requires_authentication_and_user_cannot_impersonate_with_payload(self):
        client = backend.app.test_client()
        student = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        faculty = self._login_token("Yashdeep", "25TECAD016", "FACULTY")
        suggestion = client.post("/api/suggestions", json={
            "title": "Vote identity isolation", "justification": "Automated test fixture",
            "reason": "COURSE_REQUIREMENT",
        }, headers={"Authorization": f"Bearer {student}"})
        suggestion_id = suggestion.get_json()["data"]["id"]
        try:
            denied = client.post(f"/api/suggestions/{suggestion_id}/vote")
            self.assertEqual(denied.status_code, 401)
            response = client.post(f"/api/suggestions/{suggestion_id}/vote",
                                   headers={"Authorization": f"Bearer {student}"},
                                   json={"user_id": str(backend.db.session.query(User).filter_by(name="Yashdeep").one().id)})
            self.assertEqual(response.status_code, 200)
            rows = backend.db.session.query(SuggestionVote).filter_by(suggestion_id=suggestion_id).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].user_id, backend.db.session.query(User).filter_by(name="Urvashi").one().id)
            faculty_state = client.get("/api/users/me/suggestions", headers={"Authorization": f"Bearer {faculty}"}).get_json()["data"]
            self.assertFalse(next(item for item in faculty_state if item["id"] == suggestion_id)["voted_by_me"])
        finally:
            backend.db.session.query(Suggestion).filter_by(id=suggestion_id).delete(synchronize_session=False)
            backend.db.session.commit()

    def test_concurrent_toggles_are_serialized_and_return_authoritative_state(self):
        client = backend.app.test_client()
        token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/suggestions", json={
            "title": "Concurrent vote toggle", "justification": "Automated concurrency fixture",
            "reason": "COURSE_REQUIREMENT",
        }, headers=headers)
        suggestion_id = created.get_json()["data"]["id"]
        barrier = Barrier(2)
        try:
            def submit_toggle():
                with backend.app.test_client() as thread_client:
                    barrier.wait(timeout=5)
                    return thread_client.post(f"/api/suggestions/{suggestion_id}/vote", headers=headers)

            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(lambda _index: submit_toggle(), range(2)))
            self.assertEqual([response.status_code for response in responses], [200, 200])
            states = [response.get_json()["data"] for response in responses]
            self.assertEqual(sorted(state["voted"] for state in states), [False, True])
            for state in states:
                self.assertEqual(state["vote_count"], 1 if state["voted"] else 0)
            self.assertEqual(backend.db.session.query(SuggestionVote).filter_by(suggestion_id=suggestion_id).count(), 0)
        finally:
            backend.db.session.query(Suggestion).filter_by(id=suggestion_id).delete(synchronize_session=False)
            backend.db.session.commit()

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

    def test_librarian_can_return_borrowed_loan_transactionally_and_duplicate_is_rejected(self):
        client = backend.app.test_client()
        librarian = client.post("/api/auth/login", json={"name": "Sphere", "user_id": "25LIB016", "role": "LIBRARIAN"}).get_json()["data"]
        headers = {"Authorization": f"Bearer {librarian['access_token']}"}
        loan = backend.db.session.query(Loan).filter(Loan.status == LoanStatus.BORROWED).first()
        self.assertIsNotNone(loan)
        loan_id = str(loan.id)
        response = client.post(f"/api/librarian/loans/{loan_id}/return", headers=headers)
        self.assertEqual(response.status_code, 200, response.get_json())
        backend.db.session.expire_all()
        saved = backend.db.session.get(Loan, loan_id)
        self.assertEqual(saved.status, LoanStatus.RETURNED)
        self.assertIsNotNone(saved.returned_at)
        self.assertEqual(saved.returned_to, backend.db.session.query(User).filter_by(name="Sphere").one().id)
        self.assertEqual(saved.book_copy.status, CopyStatus.AVAILABLE)
        duplicate = client.post(f"/api/librarian/loans/{loan_id}/return", headers=headers)
        self.assertEqual(duplicate.status_code, 409)

    def test_librarian_return_route_forbidden_to_student(self):
        client = backend.app.test_client()
        student = client.post("/api/auth/login", json={"name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"}).get_json()["data"]
        headers = {"Authorization": f"Bearer {student['access_token']}"}
        loan = backend.db.session.query(Loan).filter(Loan.status == LoanStatus.BORROWED).first()
        response = client.post(f"/api/librarian/loans/{loan.id}/return", headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_librarian_can_list_and_review_suggestions(self):
        client = backend.app.test_client()
        librarian = client.post("/api/auth/login", json={"name": "Sphere", "user_id": "25LIB016", "role": "LIBRARIAN"}).get_json()["data"]
        headers = {"Authorization": f"Bearer {librarian['access_token']}"}
        listed = client.get("/api/librarian/suggestions?q=Clean", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.get_json())
        first = listed.get_json()["data"]["items"][0]
        reviewed = client.post(f"/api/librarian/suggestions/{first['id']}/review", headers=headers, json={"status": "UNDER_REVIEW"})
        self.assertEqual(reviewed.status_code, 200, reviewed.get_json())
        backend.db.session.expire_all()
        saved = backend.db.session.get(Suggestion, first["id"])
        self.assertEqual(saved.status, __import__("models").SuggestionStatus.UNDER_REVIEW)
        self.assertIsNotNone(saved.reviewed_at)

    def test_user_can_read_and_mark_only_own_notifications(self):
        client = backend.app.test_client()
        student = client.post("/api/auth/login", json={"name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"}).get_json()["data"]
        headers = {"Authorization": f"Bearer {student['access_token']}"}
        listed = client.get("/api/users/me/notifications", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.get_json())
        rows = listed.get_json()["data"]["items"]
        self.assertTrue(rows)
        notification_id = rows[0]["id"]
        marked = client.post(f"/api/users/me/notifications/{notification_id}/read", headers=headers)
        self.assertEqual(marked.status_code, 200, marked.get_json())
        other = client.post("/api/auth/login", json={"name": "Dhruv", "user_id": "25DMCAD016", "role": "DEPARTMENT"}).get_json()["data"]
        forbidden = client.post(f"/api/users/me/notifications/{notification_id}/read", headers={"Authorization": f"Bearer {other['access_token']}"})
        self.assertEqual(forbidden.status_code, 404)

    def test_librarian_catalogue_create_edit_and_copy_management(self):
        client = backend.app.test_client()
        librarian = client.post("/api/auth/login", json={"name": "Sphere", "user_id": "25LIB016", "role": "LIBRARIAN"}).get_json()["data"]
        headers = {"Authorization": f"Bearer {librarian['access_token']}"}
        invalid = client.post("/api/librarian/catalogue", headers=headers, json={"title": "Bad ISBN", "isbn": "9780306406158"})
        self.assertEqual(invalid.status_code, 422)
        publisher_name = backend.db.session.query(Publisher).first().name
        category_name = backend.db.session.query(Category).first().name
        created = client.post("/api/librarian/catalogue", headers=headers, json={"title": "Test catalogue entry", "isbn": "978-0-306-40615-7", "authors": ["Test Author"], "publisher": publisher_name, "category": category_name, "publication_year": 2001})
        self.assertEqual(created.status_code, 201, created.get_json())
        book_id = created.get_json()["data"]["id"]
        try:
            duplicate = client.post("/api/librarian/catalogue", headers=headers, json={"title": "Duplicate", "isbn": "9780306406157"})
            self.assertEqual(duplicate.status_code, 409)
            edited = client.patch(f"/api/librarian/catalogue/{book_id}", headers=headers, json={"title": "Edited catalogue entry"})
            self.assertEqual(edited.status_code, 200)
            copy = client.post(f"/api/librarian/catalogue/{book_id}/copies", headers=headers, json={"accession_number": "TEST-ACC-1", "barcode": "TEST-BAR-1", "rack": "R1", "shelf": "S1"})
            self.assertEqual(copy.status_code, 201, copy.get_json())
            listing = client.get("/api/librarian/catalogue?q=Edited", headers=headers)
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(listing.get_json()["data"]["items"][0]["copies"][0]["status"], "AVAILABLE")
            self.assertEqual(listing.get_json()["data"]["items"][0]["publisher"], publisher_name)
            self.assertEqual(listing.get_json()["data"]["items"][0]["category"], category_name)
        finally:
            book = backend.db.session.get(Book, book_id)
            if book:
                backend.db.session.query(BookCopy).filter_by(book_id=book.id).delete()
                backend.db.session.delete(book)
                backend.db.session.commit()

    def test_catalogue_admin_routes_reject_students(self):
        client = backend.app.test_client()
        student = client.post("/api/auth/login", json={"name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"}).get_json()["data"]
        headers = {"Authorization": f"Bearer {student['access_token']}"}
        response = client.get("/api/librarian/catalogue", headers=headers)
        self.assertEqual(response.status_code, 403)

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
        expected_students = backend.db.session.query(User).filter_by(department_id=cse.id, role=RoleType.STUDENT, is_active=True).count()
        expected_faculty = backend.db.session.query(User).filter_by(department_id=cse.id, role=RoleType.FACULTY, is_active=True).count()
        self.assertEqual(expected_students, 12)
        self.assertEqual(expected_faculty, 5)
        self.assertEqual(data["summary"]["active_students"], expected_students)
        self.assertEqual(data["summary"]["active_faculty"], expected_faculty)
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

    def test_librarian_user_management_lists_database_records_with_filters_and_totals(self):
        client = backend.app.test_client()
        librarian_token = self._login_token("Sphere", "25LIB016", "LIBRARIAN")
        headers = {"Authorization": f"Bearer {librarian_token}"}

        page = client.get(
            "/api/librarian/users?role=STUDENT&page=2&per_page=10&sort=name&direction=asc",
            headers=headers,
        )
        self.assertEqual(page.status_code, 200, page.get_json())
        data = page.get_json()["data"]
        self.assertEqual(data["pagination"], {"page": 2, "per_page": 10, "total": 100, "pages": 10})
        self.assertEqual(len(data["items"]), 10)
        self.assertTrue(all(row["role"] == "STUDENT" and row["is_active"] for row in data["items"]))
        self.assertNotIn("email", data["items"][0])
        self.assertNotIn("password_hash", data["items"][0])
        self.assertNotIn("id", data["items"][0])
        self.assertNotIn("created_at", data["items"][0])
        self.assertEqual(data["summary"]["by_role"]["STUDENT"], {"total": 100, "enabled": 100, "disabled": 0})
        self.assertEqual(data["summary"]["by_role"]["FACULTY"], {"total": 30, "enabled": 30, "disabled": 0})
        self.assertEqual(data["summary"]["by_role"]["DEPARTMENT"], {"total": 9, "enabled": 9, "disabled": 0})
        self.assertEqual(data["summary"]["by_role"]["LIBRARIAN"], {"total": 2, "enabled": 2, "disabled": 0})
        self.assertEqual(data["summary"]["by_role"]["ADMIN"], {"total": 0, "enabled": 0, "disabled": 0})
        self.assertEqual(data["summary"]["total_accounts"], 141)
        self.assertEqual(data["summary"]["enabled_accounts"], 141)

        cse = backend.db.session.query(Department).filter_by(code="CSE").one()
        scoped = client.get(f"/api/librarian/users?role=STUDENT&department_id={cse.id}", headers=headers)
        self.assertEqual(scoped.status_code, 200, scoped.get_json())
        self.assertEqual(scoped.get_json()["data"]["pagination"]["total"], 12)
        found = client.get("/api/librarian/users?q=Student%20Demo%20001", headers=headers)
        self.assertEqual(found.status_code, 200, found.get_json())
        self.assertEqual(found.get_json()["data"]["pagination"]["total"], 1)
        self.assertEqual(found.get_json()["data"]["items"][0]["user_id"], "STD-DEMO-001")
        disabled = client.get("/api/librarian/users?account_status=disabled", headers=headers)
        self.assertEqual(disabled.status_code, 200, disabled.get_json())
        self.assertEqual(disabled.get_json()["data"]["pagination"]["total"], 0)
        self.assertEqual(disabled.get_json()["data"]["items"], [])
        invalid = client.get("/api/librarian/users?role=SUPERUSER", headers=headers)
        self.assertEqual(invalid.status_code, 422)
        unauthenticated = client.get("/api/librarian/users")
        self.assertEqual(unauthenticated.status_code, 401)

        student_token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
        forbidden = client.get("/api/librarian/users", headers={"Authorization": f"Bearer {student_token}"})
        self.assertEqual(forbidden.status_code, 403)

    def test_librarian_users_allows_admin_identity_verified_from_database(self):
        admin = User(
            name="Temporary API Test Admin", email="temporary-admin@example.test",
            password_hash="test-only-not-a-login-credential", role=RoleType.ADMIN,
            employee_id="ADMIN-API-TEST", is_active=True,
        )
        backend.db.session.add(admin)
        backend.db.session.flush()
        try:
            token = backend.create_access_token(identity=str(admin.id))
            response = backend.app.test_client().get(
                "/api/librarian/users?role=STUDENT",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            totals = response.get_json()["data"]["summary"]
            self.assertEqual(totals["total_accounts"], 142)
            self.assertEqual(totals["by_role"]["ADMIN"], {"total": 1, "enabled": 1, "disabled": 0})
        finally:
            backend.db.session.delete(admin)
            backend.db.session.flush()

    def test_department_report_accepts_single_inclusive_day_and_rejects_reversed_range(self):
        client = backend.app.test_client()
        department_token = self._login_token("Dhruv", "25DMCAD016", "DEPARTMENT")
        cse = backend.db.session.query(Department).filter_by(code="CSE").one()
        student = backend.db.session.query(User).filter_by(enrollment_id="25EMCAD016").one()
        copy = backend.db.session.query(BookCopy).join(Book).join(Book.departments).filter(
            Department.id == cse.id, BookCopy.status == CopyStatus.AVAILABLE
        ).first()
        issued_at = datetime(2026, 8, 10, 23, 59, 59)
        backend.db.session.add(Loan(
            user_id=student.id, book_copy_id=copy.id, issued_at=issued_at,
            due_at=datetime(2026, 8, 24), returned_at=datetime(2026, 8, 12),
            status=LoanStatus.RETURNED,
        ))
        backend.db.session.flush()
        response = client.get(
            f"/api/reports/department/dashboard?start_date=2026-08-10&end_date=2026-08-10&category_id={copy.book.category_id}&user_type=STUDENT",
            headers={"Authorization": f"Bearer {department_token}"},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        august = [row for row in response.get_json()["data"]["borrowing_trend"] if row["month"] == "Aug"]
        self.assertEqual(len(august), 1)
        self.assertGreaterEqual(august[0]["total_loans"], 1)
        reversed_range = client.get(
            "/api/reports/department/dashboard?start_date=2026-08-11&end_date=2026-08-10",
            headers={"Authorization": f"Bearer {department_token}"},
        )
        self.assertEqual(reversed_range.status_code, 422)

    def test_cover_lookup_api_requires_auth_and_staff_only_refresh(self):
        marker = uuid.uuid4().hex[:10]
        book = Book(title=f"Cover API Record {marker}", isbn="9780131103627")
        backend.db.session.add(book)
        backend.db.session.commit()
        original = backend.cover_service.lookup
        backend.cover_service.lookup = lambda *_args, **_kwargs: {
            "matched": True, "cover_url": "https://covers.example/verified.jpg",
            "source": "openlibrary_isbn", "cached": False,
        }
        try:
            client = backend.app.test_client()
            self.assertEqual(client.get(f"/api/books/{book.id}/cover").status_code, 401)
            student_token = self._login_token("Urvashi", "25EMCAD016", "STUDENT")
            student_headers = {"Authorization": f"Bearer {student_token}"}
            response = client.get(f"/api/books/{book.id}/cover", headers=student_headers)
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertEqual(response.get_json()["data"]["cover_url"], "https://covers.example/verified.jpg")
            self.assertEqual(client.get("/api/books/not-a-uuid/cover", headers=student_headers).status_code, 404)
            self.assertEqual(client.get(f"/api/books/{book.id}/cover?refresh=1", headers=student_headers).status_code, 403)
            librarian_token = self._login_token("Sphere", "25LIB016", "LIBRARIAN")
            staff_response = client.get(f"/api/books/{book.id}/cover?refresh=1", headers={"Authorization": f"Bearer {librarian_token}"})
            self.assertEqual(staff_response.status_code, 200, staff_response.get_json())
        finally:
            backend.cover_service.lookup = original
            backend.db.session.delete(book)
            backend.db.session.commit()

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
