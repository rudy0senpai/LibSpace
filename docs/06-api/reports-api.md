# Reports API
**Status:** Implemented

## Department dashboard
`GET /api/reports/department/dashboard`

Query parameters:
- `start_date`
- `end_date`
- `category_id`
- `user_type` (`STUDENT` or `FACULTY`)
- `suggestion_status`
- `search`

Authorization: authenticated `DEPARTMENT`, `LIBRARIAN` or `ADMIN` user. Department users are scoped to their authenticated department.

The response contains database-derived KPIs, period comparisons, borrowing trend, category borrowing, student/faculty comparison, utilization, copy status, suggestion demand, overdue trend, top suggested books and suggestion records.
