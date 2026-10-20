from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import case, func, or_

from models import (
    Book,
    BookCopy,
    CopyStatus,
    Loan,
    LoanStatus,
    RoleType,
    Suggestion,
    SuggestionStatus,
    SuggestionVote,
    User,
    db,
)

ISSUED_STATUSES = (
    LoanStatus.BORROWED,
    LoanStatus.OVERDUE,
    LoanStatus.RETURNED,
    LoanStatus.LOST,
    LoanStatus.DAMAGED,
)
PENDING_REQUEST_STATUSES = (LoanStatus.REQUESTED, LoanStatus.APPROVED)
PENDING_SUGGESTION_STATUSES = (SuggestionStatus.SUBMITTED, SuggestionStatus.UNDER_REVIEW)


def _parse_range(start_raw, end_raw):
    today = datetime.now(timezone.utc).date()
    try:
        start = date.fromisoformat(start_raw) if start_raw else None
        end = date.fromisoformat(end_raw) if end_raw else None
        if start_raw and start.isoformat() != start_raw:
            raise ValueError
        if end_raw and end.isoformat() != end_raw:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Dates must use YYYY-MM-DD format.") from None

    if start and end and start > end:
        raise ValueError("Start date must be on or before end date.")
    if not end:
        end = today
    if not start:
        start = end - timedelta(days=179)
    if (end - start).days > 3660:
        raise ValueError("Date range cannot exceed ten years.")

    days = (end - start).days + 1
    bucket = "day" if days <= 31 else "week" if days <= 180 else "month"
    return start, end, bucket


def _bucket_expression(column, bucket):
    if db.engine.dialect.name == "sqlite":
        if bucket == "day":
            return func.strftime("%Y-%m-%d", column)
        if bucket == "week":
            return func.date(column, "weekday 0", "-6 days")
        return func.strftime("%Y-%m-01", column)
    return func.date_trunc(bucket, column)


def _bucket_key(value):
    return value.strftime("%Y-%m-%d") if isinstance(value, datetime) else str(value)[:10]


def _next_bucket(value, bucket):
    if bucket == "day":
        return value + timedelta(days=1)
    if bucket == "week":
        return value + timedelta(days=7)
    return date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)


def _bucket_start(value, bucket):
    if bucket == "week":
        return value - timedelta(days=value.weekday())
    if bucket == "month":
        return value.replace(day=1)
    return value


def _bucket_label(value, bucket):
    if bucket == "week":
        return f"Week of {value.strftime('%b %d').replace(' 0', ' ')}"
    if bucket == "month":
        return value.strftime("%b %Y")
    return value.strftime("%b %d").replace(" 0", " ")


def _fill_trend(rows, start, end, bucket):
    if not rows:
        return []
    counts = {_bucket_key(key): count for key, count in rows}
    current = _bucket_start(start, bucket)
    last = _bucket_start(end, bucket)
    result = []
    while current <= last:
        key = current.isoformat()
        result.append({
            "period_start": key,
            "label": _bucket_label(current, bucket),
            "borrow_count": int(counts.get(key, 0)),
        })
        current = _next_bucket(current, bucket)
    return result


def get_librarian_analytics(start_raw=None, end_raw=None):
    """Aggregate current catalogue/circulation state and dated activity from SQL."""
    start, end, bucket = _parse_range(start_raw, end_raw)
    start_dt = datetime.combine(start, time.min)
    end_exclusive = datetime.combine(end + timedelta(days=1), time.min)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    overdue_condition = or_(
        Loan.status == LoanStatus.OVERDUE,
        (Loan.status == LoanStatus.BORROWED) & (Loan.due_at < now),
    )
    summary = {
        "total_books": db.session.query(func.count(Book.id)).scalar() or 0,
        "total_copies": db.session.query(func.count(BookCopy.id)).scalar() or 0,
        "available_copies": db.session.query(func.count(BookCopy.id)).filter(
            BookCopy.status == CopyStatus.AVAILABLE
        ).scalar() or 0,
        "borrowed_copies": db.session.query(func.count(BookCopy.id)).filter(
            BookCopy.status == CopyStatus.BORROWED
        ).scalar() or 0,
        "overdue_loans": db.session.query(func.count(Loan.id)).filter(overdue_condition).scalar() or 0,
        "pending_borrowing_requests": db.session.query(func.count(Loan.id)).filter(
            Loan.status.in_(PENDING_REQUEST_STATUSES)
        ).scalar() or 0,
        "pending_suggestions": db.session.query(func.count(Suggestion.id)).filter(
            Suggestion.status.in_(PENDING_SUGGESTION_STATUSES)
        ).scalar() or 0,
        "suggestion_votes": db.session.query(func.count(SuggestionVote.user_id)).scalar() or 0,
    }

    date_conditions = [Loan.issued_at >= start_dt, Loan.issued_at < end_exclusive]
    trend_bucket = _bucket_expression(Loan.issued_at, bucket).label("period_start")
    trend_rows = db.session.query(
        trend_bucket, func.count(Loan.id)
    ).filter(Loan.status.in_(ISSUED_STATUSES), *date_conditions).group_by(
        trend_bucket
    ).order_by(trend_bucket).all()
    borrowing_trend = _fill_trend(trend_rows, start, end, bucket)

    copy_status_rows = db.session.query(
        BookCopy.status, func.count(BookCopy.id)
    ).group_by(BookCopy.status).order_by(BookCopy.status).all()
    copy_status_distribution = [
        {"status": status.value, "count": count} for status, count in copy_status_rows
    ]

    top_borrowed_rows = db.session.query(
        Book.title, func.count(Loan.id).label("borrow_count")
    ).join(BookCopy, BookCopy.book_id == Book.id).join(
        Loan, Loan.book_copy_id == BookCopy.id
    ).filter(Loan.status.in_(ISSUED_STATUSES), *date_conditions).group_by(
        Book.id, Book.title
    ).order_by(func.count(Loan.id).desc(), Book.title.asc()).limit(8).all()
    top_borrowed_books = [
        {"title": row.title, "borrow_count": row.borrow_count} for row in top_borrowed_rows
    ]

    suggestion_date_conditions = [
        Suggestion.created_at >= start_dt,
        Suggestion.created_at < end_exclusive,
    ]
    suggestion_status_rows = db.session.query(
        Suggestion.status, func.count(Suggestion.id)
    ).filter(*suggestion_date_conditions).group_by(
        Suggestion.status
    ).order_by(Suggestion.status).all()
    suggestion_status_distribution = [
        {"status": status.value, "count": count} for status, count in suggestion_status_rows
    ]

    top_suggestion_rows = db.session.query(
        Suggestion.id,
        Suggestion.title,
        Suggestion.status,
        func.count(SuggestionVote.user_id).label("vote_count"),
    ).outerjoin(SuggestionVote, SuggestionVote.suggestion_id == Suggestion.id).filter(
        *suggestion_date_conditions
    ).group_by(Suggestion.id, Suggestion.title, Suggestion.status).order_by(
        func.count(SuggestionVote.user_id).desc(), Suggestion.created_at.asc(), Suggestion.title.asc()
    ).limit(8).all()
    top_suggestions = [
        {"id": str(row.id), "title": row.title, "status": row.status.value, "vote_count": row.vote_count}
        for row in top_suggestion_rows
    ]

    user_id_expr = case(
        (User.role == RoleType.STUDENT, User.enrollment_id),
        else_=User.employee_id,
    )
    overdue_rows = db.session.query(
        Loan.id, Book.title, User.name, user_id_expr, Loan.due_at, BookCopy.accession_number
    ).join(User, Loan.user_id == User.id).join(
        BookCopy, Loan.book_copy_id == BookCopy.id
    ).join(Book, BookCopy.book_id == Book.id).filter(
        overdue_condition
    ).order_by(Loan.due_at.asc()).limit(8).all()
    overdue_loans = [
        {
            "id": str(row.id),
            "book_title": row.title,
            "borrower": row.name,
            "user_id": row[3],
            "due_at": row.due_at.isoformat(),
            "accession_number": row.accession_number,
        }
        for row in overdue_rows
    ]

    return {
        "summary": summary,
        "borrowing_trend": borrowing_trend,
        "copy_status_distribution": copy_status_distribution,
        "top_borrowed_books": top_borrowed_books,
        "suggestion_status_distribution": suggestion_status_distribution,
        "top_suggestions": top_suggestions,
        "overdue_loans": overdue_loans,
        "meta": {
            "source": f"{db.engine.dialect.name.upper()} Database",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "bucket": bucket,
            "timezone": "UTC",
            "range_semantics": "Inclusive dates; timestamp queries use [start midnight, midnight after end).",
            "summary_scope": "Current catalogue/copy/overdue/request/suggestion snapshot; activity charts use the selected issue/submission dates.",
        },
    }
