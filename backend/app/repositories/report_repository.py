from datetime import date, datetime, timedelta
from psycopg import sql
from app.core.database import get_conn

class ReportRepository:
    def _query(self, query, params=()):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def scope(self, department_id):
        rows=self._query("SELECT id, code, name, short_name FROM departments WHERE id=%s",(department_id,))
        return rows[0] if rows else None

    def summary(self, department_id, start, end):
        q='''
        WITH relevant_books AS (SELECT DISTINCT book_id FROM book_departments WHERE department_id=%s),
        active_users AS (SELECT id, role FROM users WHERE department_id=%s AND is_active=true),
        active_loans AS (
          SELECT l.* FROM loans l JOIN users u ON u.id=l.user_id JOIN book_copies bc ON bc.id=l.book_copy_id
          WHERE u.department_id=%s AND l.returned_at IS NULL AND l.status IN ('BORROWED','OVERDUE')
        ),
        dept_suggestions AS (SELECT s.* FROM suggestions s JOIN users u ON u.id=s.submitted_by WHERE u.department_id=%s)
        SELECT
          (SELECT COUNT(*) FROM relevant_books) AS department_books,
          (SELECT COUNT(*) FROM book_copies bc WHERE bc.book_id IN (SELECT book_id FROM relevant_books) AND bc.status='AVAILABLE') AS available_copies,
          (SELECT COUNT(*) FROM active_loans) AS currently_borrowed,
          (SELECT COUNT(*) FROM active_loans WHERE due_at < NOW()) AS overdue_books,
          (SELECT COUNT(*) FROM active_users WHERE role='STUDENT' AND id IN (SELECT user_id FROM loans WHERE issued_at >= %s AND issued_at < %s)) AS active_students,
          (SELECT COUNT(*) FROM active_users WHERE role='FACULTY' AND id IN (SELECT user_id FROM loans WHERE issued_at >= %s AND issued_at < %s)) AS active_faculty,
          (SELECT COUNT(*) FROM dept_suggestions WHERE status IN ('SUBMITTED','UNDER_REVIEW')) AS pending_suggestions,
          (SELECT COUNT(*) FROM suggestion_votes v WHERE v.suggestion_id IN (SELECT id FROM dept_suggestions)) AS suggestion_support
        '''
        return self._query(q,(department_id,department_id,department_id,department_id,start,end,start,end))[0]

    def previous_summary(self, department_id, start, end):
        duration=end-start
        return self.summary(department_id,start-duration,start)

    def borrowing_trend(self, department_id, start, end):
        q='''SELECT DATE_TRUNC('month',l.issued_at)::date AS month, COUNT(*) AS total_loans,
                    COUNT(*) FILTER (WHERE u.role='STUDENT') AS student_loans,
                    COUNT(*) FILTER (WHERE u.role='FACULTY') AS faculty_loans
             FROM loans l JOIN users u ON u.id=l.user_id JOIN book_copies bc ON bc.id=l.book_copy_id
             JOIN book_departments bd ON bd.book_id=bc.book_id
             WHERE bd.department_id=%s AND l.issued_at >= %s AND l.issued_at < %s
             GROUP BY 1 ORDER BY 1'''
        return self._query(q,(department_id,start,end))

    def borrowing_by_category(self, department_id,start,end,category_id=None,user_type=None):
        q='''SELECT c.id AS category_id, COALESCE(c.name,'Uncategorised') AS category_name, COUNT(*) AS borrow_count
             FROM loans l JOIN users u ON u.id=l.user_id JOIN book_copies bc ON bc.id=l.book_copy_id
             JOIN book_departments bd ON bd.book_id=bc.book_id LEFT JOIN books b ON b.id=bc.book_id
             LEFT JOIN categories c ON c.id=b.category_id
             WHERE bd.department_id=%s AND l.issued_at >= %s AND l.issued_at < %s'''
        p=[department_id,start,end]
        if category_id: q+=' AND b.category_id=%s'; p.append(category_id)
        if user_type: q+=' AND u.role=%s'; p.append(user_type)
        q+=' GROUP BY c.id, c.name ORDER BY borrow_count DESC'
        return self._query(q,p)

    def student_vs_faculty(self, department_id,start,end):
        q='''SELECT DATE_TRUNC('month',l.issued_at)::date AS period,
                    COUNT(*) FILTER (WHERE u.role='STUDENT') AS students,
                    COUNT(*) FILTER (WHERE u.role='FACULTY') AS faculty
             FROM loans l JOIN users u ON u.id=l.user_id JOIN book_copies bc ON bc.id=l.book_copy_id
             JOIN book_departments bd ON bd.book_id=bc.book_id
             WHERE bd.department_id=%s AND l.issued_at >= %s AND l.issued_at < %s
             GROUP BY 1 ORDER BY 1'''
        return self._query(q,(department_id,start,end))

    def copy_status(self,department_id):
        q='''SELECT bc.status::text AS status, COUNT(*) AS count
             FROM book_copies bc JOIN book_departments bd ON bd.book_id=bc.book_id
             WHERE bd.department_id=%s GROUP BY bc.status ORDER BY count DESC'''
        rows=self._query(q,(department_id,)); total=sum(int(r['count']) for r in rows)
        return [{**r,'percentage':round((int(r['count'])/total*100),1) if total else 0} for r in rows]

    def utilization(self,department_id,start,end):
        q='''SELECT DATE_TRUNC('month',l.issued_at)::date AS period,
                    COUNT(DISTINCT l.book_copy_id) AS borrowed_copies,
                    (SELECT COUNT(DISTINCT bc.id) FROM book_copies bc JOIN book_departments bd2 ON bd2.book_id=bc.book_id WHERE bd2.department_id=%s) AS relevant_copies
             FROM loans l JOIN book_copies bc ON bc.id=l.book_copy_id JOIN book_departments bd ON bd.book_id=bc.book_id
             WHERE bd.department_id=%s AND l.issued_at >= %s AND l.issued_at < %s
             GROUP BY 1 ORDER BY 1'''
        rows=self._query(q,(department_id,department_id,start,end))
        return [{**r,'utilization_rate':round((int(r['borrowed_copies'])/int(r['relevant_copies'])*100),1) if r['relevant_copies'] else 0} for r in rows]

    def overdue_trend(self,department_id,start,end):
        q='''SELECT DATE_TRUNC('month',l.due_at)::date AS period, COUNT(*) AS overdue_count
             FROM loans l JOIN users u ON u.id=l.user_id JOIN book_copies bc ON bc.id=l.book_copy_id
             JOIN book_departments bd ON bd.book_id=bc.book_id
             WHERE bd.department_id=%s AND l.due_at < NOW() AND l.due_at >= %s AND l.due_at < %s
             GROUP BY 1 ORDER BY 1'''
        return self._query(q,(department_id,start,end))

    def suggestion_demand(self,department_id,start,end,category_id=None,status=None):
        q='''SELECT c.id AS category_id, COALESCE(c.name,'Uncategorised') AS category_name, COUNT(*) AS suggestion_count
             FROM suggestions s JOIN users u ON u.id=s.submitted_by LEFT JOIN categories c ON c.id=s.category_id
             WHERE u.department_id=%s AND s.created_at >= %s AND s.created_at < %s'''
        p=[department_id,start,end]
        if category_id: q+=' AND s.category_id=%s'; p.append(category_id)
        if status: q+=' AND s.status=%s'; p.append(status)
        q+=' GROUP BY c.id, c.name ORDER BY suggestion_count DESC'
        return self._query(q,p)

    def suggestion_status(self,department_id):
        q='''SELECT s.status::text AS status, COUNT(*) AS count FROM suggestions s JOIN users u ON u.id=s.submitted_by
             WHERE u.department_id=%s GROUP BY s.status ORDER BY count DESC'''
        return self._query(q,(department_id,))

    def top_books(self,department_id):
        q='''SELECT s.title, COUNT(v.user_id) AS vote_count, MAX(s.created_at) AS created_at
             FROM suggestions s JOIN users u ON u.id=s.submitted_by LEFT JOIN suggestion_votes v ON v.suggestion_id=s.id
             WHERE u.department_id=%s GROUP BY s.id,s.title ORDER BY vote_count DESC, created_at ASC, s.title ASC LIMIT 5'''
        return self._query(q,(department_id,))

    def student_faculty_suggestions(self,department_id,start,end):
        q='''SELECT u.role::text AS requester_type, COUNT(*) AS suggestion_count,
                    (SELECT COUNT(*) FROM suggestion_votes v WHERE v.suggestion_id IN (SELECT s2.id FROM suggestions s2 JOIN users u2 ON u2.id=s2.submitted_by WHERE u2.department_id=%s AND u2.role=u.role)) AS vote_support
             FROM suggestions s JOIN users u ON u.id=s.submitted_by
             WHERE u.department_id=%s AND s.created_at >= %s AND s.created_at < %s AND u.role IN ('STUDENT','FACULTY')
             GROUP BY u.role ORDER BY u.role'''
        return self._query(q,(department_id,department_id,start,end))

    def suggestions(self,department_id,start,end,search=None,status=None,category_id=None,user_type=None,limit=50,offset=0):
        q='''SELECT s.id,s.title,s.author,s.reason::text AS reason,s.status::text AS status,s.created_at,
                    u.name AS requester,u.role::text AS requester_type,d.code AS department,COALESCE(v.vote_count,0) AS votes
             FROM suggestions s JOIN users u ON u.id=s.submitted_by JOIN departments d ON d.id=u.department_id
             LEFT JOIN (SELECT suggestion_id,COUNT(*) AS vote_count FROM suggestion_votes GROUP BY suggestion_id) v ON v.suggestion_id=s.id
             WHERE u.department_id=%s AND s.created_at >= %s AND s.created_at < %s'''
        p=[department_id,start,end]
        if search: q+=' AND (s.title ILIKE %s OR s.author ILIKE %s OR s.justification ILIKE %s)'; term='%'+search+'%'; p += [term,term,term]
        if status: q+=' AND s.status=%s'; p.append(status)
        if category_id: q+=' AND s.category_id=%s'; p.append(category_id)
        if user_type: q+=' AND u.role=%s'; p.append(user_type)
        q+=' ORDER BY s.created_at DESC LIMIT %s OFFSET %s'; p += [limit,offset]
        return self._query(q,p)
