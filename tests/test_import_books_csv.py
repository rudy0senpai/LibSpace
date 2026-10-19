import unittest
import tempfile
from pathlib import Path
from flask import Flask

from backend.import_books_csv import identity, import_rows, norm, norm_isbn
from backend.models import db, Book, Author, Publisher, Category, Department, book_departments


class BookCsvImportHelpersTests(unittest.TestCase):
    def test_isbn_normalization_validates_checksum(self):
        self.assertEqual(norm_isbn("978-0-306-40615-7"), "9780306406157")
        self.assertEqual(norm_isbn("0-306-40615-2"), "0306406152")
        self.assertIsNone(norm_isbn("9780306406158"))
        self.assertIsNone(norm_isbn(""))

    def test_fallback_identity_preserves_distinct_editions_and_authors(self):
        base = {"title": "Same title", "author": "A. Author", "edition": "First", "publication_year": "2001", "publisher": "Pub"}
        self.assertEqual(identity(base), identity({key: f" {value.upper()} " for key, value in base.items()}))
        self.assertNotEqual(identity(base), identity({**base, "edition": "Second"}))
        self.assertNotEqual(identity(base), identity({**base, "author": "Different author"}))

    def test_normalizes_whitespace_and_case(self):
        self.assertEqual(norm("  AI   & Data Science "), "ai & data science")


class LegacyCsvBlankIsbnGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask("legacy-csv-guard-tests")
        cls.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(cls.app)

    def setUp(self):
        self.context = self.app.app_context(); self.context.push(); db.create_all()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.context.pop()

    def test_missing_isbn_rows_are_rejected_instead_of_creating_blank_books(self):
        row = {
            "book_id":"old-1", "title":"Legacy record", "author":"A. Author", "department":"CSE",
            "category":"Computing", "publisher":"Publisher", "publication_year":"2000", "edition":"",
            "isbn":"", "language":"English", "total_copies":"2", "available_copies":"2",
            "shelf_location":"R1", "description":"", "record_type":"generated",
        }
        with tempfile.TemporaryDirectory() as directory:
            stats = import_rows(
                self.app, db, Book, Author, Publisher, Category, Department, book_departments,
                [(2, row)], Path(directory) / "rejected.csv",
            )
        self.assertEqual(stats["new_books"], 0)
        self.assertEqual(stats["missing_isbn"], 1)
        self.assertEqual(stats["rejected"], 1)
        self.assertEqual(db.session.query(Book).count(), 0)


if __name__ == "__main__":
    unittest.main()
