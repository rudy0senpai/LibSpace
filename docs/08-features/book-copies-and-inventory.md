# Feature: Book Copies and Inventory
**Status:** Planned · **Priority:** MVP
```text
Book → Physical Copy → Accession Number → QR/Barcode → Shelf/Rack → Status
```
Copy fields: copy_id, book_id, accession_number, barcode/QR, shelf, rack, status, condition, acquired_at. Statuses: AVAILABLE, BORROWED, RESERVED, LOST, DAMAGED, MAINTENANCE, WITHDRAWN. Librarians add/update/withdraw copies; changes are audit-logged.
