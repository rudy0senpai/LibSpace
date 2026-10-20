import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-for-libsphere-analytics-32chars"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as backend  # noqa: E402
from models import (  # noqa: E402
    Book, BookCopy, CopyStatus, Department, Loan, LoanStatus, RoleType,
    Suggestion, SuggestionReason, SuggestionStatus, SuggestionVote, User,
)


class LibrarianAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = backend.app.app_context()
        cls.context.push()
        backend.app.config.update(
            TESTING=True, APP_ENV="testing",
            JWT_SECRET_KEY="test-only-secret-key-for-libsphere-analytics-32chars",
        )
        backend.db.create_all()
        cls.department = Department(code="ANALYTICS", name="Analytics Test", short_name="AT")
        backend.db.session.add(cls.department)
        backend.db.session.flush()
        cls.student = User(
            name="Analytics Student", email="analytics-student@libsphere.test",
            password_hash="test-only-not-used", role=RoleType.STUDENT,
            department_id=cls.department.id, enrollment_id="AN-001",
        )
        cls.faculty = User(
            name="Analytics Faculty", email="analytics-faculty@libsphere.test",
            password_hash="test-only-not-used", role=RoleType.FACULTY,
            department_id=cls.department.id, employee_id="AN-F-001",
        )
        cls.librarian = User(
            name="Analytics Librarian", email="analytics-librarian@libsphere.test",
            password_hash="test-only-not-used", role=RoleType.LIBRARIAN,
            employee_id="AN-L-001",
        )
        backend.db.session.add_all([cls.student, cls.faculty, cls.librarian])
        backend.db.session.commit()
        cls.client = backend.app.test_client()

    @classmethod
    def tearDownClass(cls):
        backend.db.session.remove()
        backend.db.drop_all()
        cls.context.pop()

    def setUp(self):
        now = datetime.utcnow().replace(microsecond=0)
        self.book = Book(title="Analytics Test Book")
        backend.db.session.add(self.book)
        backend.db.session.flush()
        self.available_copy = self._copy("AN-C-001", CopyStatus.AVAILABLE)
        self.overdue_copy = self._copy("AN-C-002", CopyStatus.BORROWED)
        self.request_copy = self._copy("AN-C-003", CopyStatus.RESERVED)
        self.returned_copy = self._copy("AN-C-004", CopyStatus.AVAILABLE)
        backend.db.session.flush()
        self.overdue_loan = Loan(
            user_id=self.student.id, book_copy_id=self.overdue_copy.id,
            issued_at=now - timedelta(days=10), due_at=now - timedelta(days=4),
            status=LoanStatus.OVERDUE,
        )
        self.request_loan = Loan(
            user_id=self.student.id, book_copy_id=self.request_copy.id,
            issued_at=now, due_at=now + timedelta(days=14), status=LoanStatus.REQUESTED,
        )
        self.returned_loan = Loan(
            user_id=self.faculty.id, book_copy_id=self.returned_copy.id,
            issued_at=now - timedelta(days=3), due_at=now + timedelta(days=7),
            returned_at=now - timedelta(days=1), status=LoanStatus.RETURNED,
        )
        backend.db.session.add_all([self.overdue_loan, self.request_loan, self.returned_loan])
        self.suggestion = Suggestion(
            title="Analytics Suggestion", author="Test Author", justification="Course need",
            reason=SuggestionReason.COURSE_REQUIREMENT, status=SuggestionStatus.SUBMITTED,
            submitted_by=self.student.id, created_at=now - timedelta(days=2),
        )
        backend.db.session.add(self.suggestion)
        backend.db.session.flush()
        backend.db.session.add_all([
            SuggestionVote(suggestion_id=self.suggestion.id, user_id=self.student.id),
            SuggestionVote(suggestion_id=self.suggestion.id, user_id=self.faculty.id),
        ])
        backend.db.session.commit()
        self.now = now

    def tearDown(self):
        for row in [self.overdue_loan, self.request_loan, self.returned_loan, self.suggestion]:
            backend.db.session.delete(row)
        for row in [self.available_copy, self.overdue_copy, self.request_copy, self.returned_copy]:
            backend.db.session.delete(row)
        backend.db.session.delete(self.book)
        backend.db.session.commit()

    def _copy(self, accession, status):
        copy = BookCopy(
            book_id=self.book.id, accession_number=accession, barcode=f"BAR-{accession}",
            rack="A", shelf="1", status=status, acquired_at=datetime.utcnow().date(),
        )
        backend.db.session.add(copy)
        return copy

    def _token(self, user):
        return backend.create_access_token(identity=str(user.id))

    def _get(self, path, user=None):
        user = user or self.librarian
        return self.client.get(path, headers={"Authorization": f"Bearer {self._token(user)}"})

    def test_librarian_dashboard_aggregates_database_records_and_date_range(self):
        start = (self.now.date() - timedelta(days=15)).isoformat()
        end = self.now.date().isoformat()
        response = self._get(f"/api/reports/librarian/dashboard?start_date={start}&end_date={end}")
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["summary"]["total_books"], 1)
        self.assertEqual(data["summary"]["total_copies"], 4)
        self.assertEqual(data["summary"]["available_copies"], 2)
        self.assertEqual(data["summary"]["borrowed_copies"], 1)
        self.assertEqual(data["summary"]["overdue_loans"], 1)
        self.assertEqual(data["summary"]["pending_borrowing_requests"], 1)
        self.assertEqual(data["summary"]["pending_suggestions"], 1)
        self.assertEqual(sum(point["borrow_count"] for point in data["borrowing_trend"]), 2)
        self.assertEqual(data["top_borrowed_books"][0]["borrow_count"], 2)
        self.assertEqual(data["copy_status_distribution"], [
            {"status": "AVAILABLE", "count": 2},
            {"status": "BORROWED", "count": 1},
            {"status": "RESERVED", "count": 1},
        ])
        self.assertEqual(data["suggestion_status_distribution"], [{"status": "SUBMITTED", "count": 1}])
        self.assertEqual(data["top_suggestions"][0]["vote_count"], 2)
        self.assertEqual(len(data["overdue_loans"]), 1)
        self.assertEqual(data["meta"]["start_date"], start)
        self.assertEqual(data["meta"]["end_date"], end)

    def test_librarian_analytics_empty_range_and_invalid_range(self):
        empty = self._get("/api/reports/librarian/dashboard?start_date=1900-01-01&end_date=1900-01-31")
        self.assertEqual(empty.status_code, 200)
        data = empty.get_json()["data"]
        self.assertEqual(data["borrowing_trend"], [])
        self.assertEqual(data["top_borrowed_books"], [])
        self.assertEqual(data["suggestion_status_distribution"], [])
        invalid = self._get("/api/reports/librarian/dashboard?start_date=2026-02-30&end_date=2026-03-01")
        self.assertEqual(invalid.status_code, 422)
        reversed_range = self._get("/api/reports/librarian/dashboard?start_date=2026-03-02&end_date=2026-03-01")
        self.assertEqual(reversed_range.status_code, 422)

    def test_librarian_analytics_remains_role_protected(self):
        response = self._get("/api/reports/librarian/dashboard", self.student)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
