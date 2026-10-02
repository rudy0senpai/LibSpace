# Feature: Reports and Analytics
**Status:** Implemented — Department dashboard foundation

The Department Dashboard reads analytics from PostgreSQL through FastAPI. No screenshot numbers are used as production data.

## Metrics
- Department Books: distinct books linked through `book_departments`.
- Available Copies: relevant physical copies with status `AVAILABLE`.
- Currently Borrowed: active department user loans with no return.
- Overdue Books: active loans whose due date has passed.
- Active Students/Faculty: department users with library activity during the selected period.
- Pending Suggestions: suggestions in `SUBMITTED` or `UNDER_REVIEW`.
- Suggestion Support: votes on department suggestions.
- Utilization: distinct borrowed copies per month divided by distinct relevant copies.

## Data path
React → FastAPI → report service → report repository → PostgreSQL.

## Visual sections
KPI cards; monthly borrowing; borrowing by category; student vs faculty; book utilization; copy status; suggestion demand; suggestions table; top suggested books; recent suggestions.
