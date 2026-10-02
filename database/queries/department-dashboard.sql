-- Department dashboard SQL reference queries.
-- The FastAPI repository executes equivalent parameterized statements.

-- KPI: books relevant to department
SELECT COUNT(DISTINCT b.id)
FROM books b
JOIN book_departments bd ON bd.book_id=b.id
WHERE bd.department_id=$1;

-- KPI: copy status
SELECT bc.status, COUNT(*)
FROM book_copies bc
JOIN book_departments bd ON bd.book_id=bc.book_id
WHERE bd.department_id=$1
GROUP BY bc.status
ORDER BY bc.status;

-- Monthly borrowing
SELECT DATE_TRUNC('month',l.issued_at)::date AS month,
       COUNT(*) AS total_loans,
       COUNT(*) FILTER (WHERE u.role='STUDENT') AS student_loans,
       COUNT(*) FILTER (WHERE u.role='FACULTY') AS faculty_loans
FROM loans l
JOIN users u ON u.id=l.user_id
JOIN book_copies bc ON bc.id=l.book_copy_id
JOIN book_departments bd ON bd.book_id=bc.book_id
WHERE bd.department_id=$1
  AND l.issued_at >= $2 AND l.issued_at < $3
GROUP BY 1 ORDER BY 1;

-- Borrowing by category
SELECT c.name AS category_name, COUNT(*) AS borrow_count
FROM loans l
JOIN users u ON u.id=l.user_id
JOIN book_copies bc ON bc.id=l.book_copy_id
JOIN books b ON b.id=bc.book_id
JOIN book_departments bd ON bd.book_id=b.id
JOIN categories c ON c.id=b.category_id
WHERE bd.department_id=$1 AND l.issued_at >= $2 AND l.issued_at < $3
GROUP BY c.name ORDER BY borrow_count DESC;

-- Suggestions by category
SELECT c.name AS category_name, COUNT(*) AS suggestion_count
FROM suggestions s
JOIN users u ON u.id=s.submitted_by
LEFT JOIN categories c ON c.id=s.category_id
WHERE u.department_id=$1 AND s.created_at >= $2 AND s.created_at < $3
GROUP BY c.name ORDER BY suggestion_count DESC;

-- Top suggested books
SELECT s.title, COUNT(v.user_id) AS vote_count, MAX(s.created_at) AS created_at
FROM suggestions s
JOIN users u ON u.id=s.submitted_by
LEFT JOIN suggestion_votes v ON v.suggestion_id=s.id
WHERE u.department_id=$1
GROUP BY s.id,s.title
ORDER BY vote_count DESC, created_at ASC, s.title ASC
LIMIT 5;
