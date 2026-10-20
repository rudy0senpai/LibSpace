import json
import unittest
from datetime import date, datetime, timedelta
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs

from flask import Flask

from backend.import_academic_textbooks import (
    import_verified, normalize, normalize_isbn, valid_isbn, verify_rows,
)
from backend.models import (
    db, Book, BookCopy, Author, Publisher, Category, Department, BookSourceMetadata,
    User, Loan, CopyStatus, RoleType, LoanStatus,
)


def sample_row(isbn='9780131103627', book_id='1'):
    return {
        'book_id': book_id, 'title': 'The C Programming Language',
        'authors': 'Brian W. Kernighan; Dennis M. Ritchie', 'isbn': isbn,
        'isbn_type': 'ISBN_13', 'programme': 'B.Tech AIDS',
        'subject_area': 'Computer Science', 'subjects': 'C; programming',
        'publisher': 'Prentice Hall', 'publication_year': '1988', 'edition': '2nd',
        'language': 'eng', 'cover_url': 'https://covers.openlibrary.org/b/id/1-L.jpg',
        'source_name': 'Open Library', 'source_record_url': 'https://openlibrary.org/works/OL123W',
    }


class FakeResponse(BytesIO):
    def __enter__(self): return self
    def __exit__(self, *_args): self.close()


class AcademicImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask('academic-import-tests')
        cls.app.config.update(SQLALCHEMY_DATABASE_URI='sqlite://', SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(cls.app)

    def setUp(self):
        self.ctx = self.app.app_context(); self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def test_isbn10_and_isbn13_checksums(self):
        self.assertTrue(valid_isbn('0-306-40615-2'))
        self.assertTrue(valid_isbn('978-0-13-110362-7'))
        self.assertFalse(valid_isbn('9780131103628'))
        self.assertFalse(valid_isbn(''))
        self.assertEqual(normalize_isbn('0-306-40615-2'), '0306406152')

    def test_preflight_rejects_duplicate_isbn_and_bad_title_associations(self):
        rows = [sample_row(book_id='1'), sample_row(book_id='2'), sample_row(isbn='9780131103627', book_id='3')]
        # Make the third row a separate unique ISBN whose edition record is a different book.
        rows[2]['isbn'] = '9780201616224'
        def opener(request, timeout=30):
            keys = parse_qs(urlparse(request.full_url).query)['bibkeys'][0].split(',')
            payload = {}
            for key in keys:
                isbn = key.split(':', 1)[1]
                if isbn == '9780201616224':
                    payload[key] = {'title': 'Different title', 'authors': [{'name': 'Different author'}]}
                else:
                    payload[key] = {'title': 'The C Programming Language', 'authors': [{'name': 'Brian W. Kernighan'}, {'name': 'Dennis M. Ritchie'}], 'publishers': [{'name':'Prentice Hall'}], 'publish_date':'1988'}
            return FakeResponse(json.dumps(payload).encode())
        report, summary = verify_rows(rows, opener=opener, sleep=lambda _seconds: None)
        self.assertEqual(summary['duplicate_isbn_values'], 1)
        self.assertEqual(summary['duplicate_rows_beyond_first'], 1)
        self.assertEqual(summary['rejected_records'], 3)
        self.assertTrue(all(row['rejected'] for row in report))

    def test_import_is_idempotent_and_does_not_create_physical_copies(self):
        row = sample_row()
        record = {'row': row, 'evidence': {'matched': True, 'edition_publishers':['Prentice Hall'], 'edition_publish_date':'1988', 'edition_record_url':'https://openlibrary.org/isbn/9780131103627'}, 'rejected':False, 'reasons':[]}
        models = (Book, BookCopy, Author, Publisher, Category, Department, BookSourceMetadata)
        first = import_verified(self.app, db, models, [record])
        second = import_verified(self.app, db, models, [record])
        self.assertEqual(first['created_books'], 1)
        self.assertEqual(second['created_books'], 0)
        self.assertEqual(second['matched_existing'], 1)
        self.assertEqual(db.session.query(Book).count(), 1)
        self.assertEqual(db.session.query(BookCopy).count(), 0)
        imported = db.session.query(Book).one()
        self.assertEqual(imported.isbn, '9780131103627')
        self.assertIsNone(imported.description)
        source = db.session.query(BookSourceMetadata).filter_by(book_id=imported.id).one()
        self.assertEqual(json.loads(source.metadata_json)['programme'], 'B.Tech AIDS')
        self.assertEqual(source.source_name, 'LibSphere_Academic_Textbooks_1000.csv')

    def test_import_preserves_unrelated_user_and_loan_history(self):
        department = Department(code='CSE', name='Computer Science', short_name='CSE')
        db.session.add(department); db.session.flush()
        user = User(name='Existing user', email='existing@example.test', password_hash='hash', role=RoleType.STUDENT, department_id=department.id)
        existing_book = Book(title='Unrelated existing title', isbn='9780000000002', language='eng')
        db.session.add_all([user, existing_book]); db.session.flush()
        copy = BookCopy(book_id=existing_book.id, accession_number='ACC-1', barcode='BAR-1', rack='R1', shelf='S1', status=CopyStatus.BORROWED, condition='GOOD', acquired_at=date(2024,1,1))
        db.session.add(copy); db.session.flush()
        loan = Loan(user_id=user.id, book_copy_id=copy.id, issued_at=datetime(2024,1,1), due_at=datetime(2024,1,15), status=LoanStatus.BORROWED)
        db.session.add(loan); db.session.commit()
        original = (db.session.query(User).count(), db.session.query(Loan).count(), db.session.query(BookCopy).count(), str(user.id), str(loan.id))

        row = sample_row()
        record = {'row': row, 'evidence': {'matched': True, 'edition_publishers':['Prentice Hall'], 'edition_publish_date':'1988'}, 'rejected':False, 'reasons':[]}
        import_verified(self.app, db, (Book, BookCopy, Author, Publisher, Category, Department, BookSourceMetadata), [record])
        current = (db.session.query(User).count(), db.session.query(Loan).count(), db.session.query(BookCopy).count(), str(db.session.query(User).filter_by(email='existing@example.test').one().id), str(db.session.query(Loan).one().id))
        self.assertEqual(current, original)


if __name__ == '__main__':
    unittest.main()
