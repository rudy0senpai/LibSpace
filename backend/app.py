import os
import uuid
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pathlib import Path
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy.engine import URL
from sqlalchemy import func, text, case, inspect, String, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash
from werkzeug.exceptions import HTTPException

from config import Config
from models import db, User, RoleType, Department, Book, BookCopy, Loan, Suggestion, SuggestionVote, Category, CopyStatus, LoanStatus, SuggestionStatus, SuggestionReason, Author, Publisher, Notification, NotificationType, AuditLog
from identity import canonicalize_name, canonicalize_role, canonicalize_user_id

BACKEND_INSTANCE_DIR = Path(__file__).resolve().parent / "instance"
BACKEND_INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, instance_path=str(BACKEND_INSTANCE_DIR))
app.config.from_object(Config)


db.init_app(app)
jwt = JWTManager(app)
CORS(
    app,
    origins=app.config.get("CORS_ORIGINS", ("http://localhost:5173",)),
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


@jwt.unauthorized_loader
def missing_authorization(_reason):
    return jsonify({"status": "error", "error": {
        "code": "MISSING_AUTHORIZATION", "message": "Authentication is required."
    }}), 401


@jwt.invalid_token_loader
def invalid_authorization(_reason):
    return jsonify({"status": "error", "error": {
        "code": "INVALID_TOKEN", "message": "The authentication token is invalid."
    }}), 401


@jwt.expired_token_loader
def expired_authorization(_jwt_header, _jwt_payload):
    return jsonify({"status": "error", "error": {
        "code": "EXPIRED_TOKEN", "message": "The authentication token has expired."
    }}), 401


@app.errorhandler(SQLAlchemyError)
def database_error(error):
    db.session.rollback()
    app.logger.error("Database request failed: %s", error)
    return jsonify({"status": "error", "error": {
        "code": "DATABASE_UNAVAILABLE", "message": "The database request could not be completed."
    }}), 503


@app.errorhandler(HTTPException)
def http_error(error):
    if not request.path.startswith("/api/"):
        return error
    return jsonify({"status": "error", "error": {
        "code": f"HTTP_{error.code}", "message": error.description
    }}), error.code


@app.errorhandler(Exception)
def unexpected_api_error(error):
    if not request.path.startswith("/api/"):
        raise error
    app.logger.exception("Unhandled API error")
    return jsonify({"status": "error", "error": {
        "code": "INTERNAL_SERVER_ERROR", "message": "The request could not be completed."
    }}), 500


USER_TYPES = {"STUDENT", "FACULTY"}
SUGGESTION_STATUSES = {
    "SUBMITTED", "UNDER_REVIEW", "APPROVED", "ORDERED",
    "AVAILABLE", "REJECTED", "DUPLICATE", "ALREADY_AVAILABLE"
}


def month_bucket(column):
    if db.engine.dialect.name == "sqlite":
        return func.strftime("%Y-%m-01", column)
    return func.date_trunc("month", column)


def month_label(value):
    if isinstance(value, datetime):
        return value.strftime("%b")
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%b")


def validate_filters():
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    category_id = (request.args.get("category_id") or "").strip() or None
    user_type = (request.args.get("user_type") or "").strip().upper() or None
    suggestion_status = (request.args.get("suggestion_status") or "").strip().upper() or None
    search = request.args.get("search")

    try:
        if start_date:
            parsed = datetime.strptime(start_date, "%Y-%m-%d")
            if parsed.strftime("%Y-%m-%d") != start_date:
                raise ValueError()

        if end_date:
            parsed = datetime.strptime(end_date, "%Y-%m-%d")
            if parsed.strftime("%Y-%m-%d") != end_date:
                raise ValueError()

        if start_date and end_date and start_date > end_date:
            raise ValueError()

    except ValueError:
        raise ValueError("Invalid dates")

    if user_type and user_type not in USER_TYPES:
        raise ValueError("Invalid user type")

    if suggestion_status and suggestion_status not in SUGGESTION_STATUSES:
        raise ValueError("Invalid suggestion status")

    if category_id:
        try:
            category_id = str(uuid.UUID(category_id))
        except (TypeError, ValueError):
            raise ValueError("Invalid category ID")
        if not db.session.get(Category, category_id):
            raise ValueError("Unknown category ID")

    if search:
        search = search.strip()
        if len(search) > 200:
            raise ValueError("Search is too long")
        if not search:
            search = None

    return {
        "start_date": start_date,
        "end_date": end_date,
        "category_id": category_id,
        "user_type": user_type,
        "suggestion_status": suggestion_status,
        "search": search
    }


def filter_department_suggestions(query, filters, start_dt, end_dt):
    query = query.filter(Suggestion.created_at >= start_dt, Suggestion.created_at < end_dt)
    if filters.get("category_id"):
        query = query.filter(Suggestion.category_id == filters["category_id"])
    if filters.get("user_type"):
        query = query.filter(User.role == RoleType(filters["user_type"]))
    if filters.get("suggestion_status"):
        query = query.filter(Suggestion.status == SuggestionStatus(filters["suggestion_status"]))
    if filters.get("search"):
        search = filters["search"]
        query = query.filter(
            (Suggestion.title.ilike(f"%{search}%")) |
            (Suggestion.author.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )
    return query


def get_department_dashboard_data(department_id, filters):
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    category_id = filters.get("category_id")
    user_type = filters.get("user_type")
    suggestion_status = filters.get("suggestion_status")
    search = filters.get("search")

    today = datetime.now()
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    elif end_date:
        start_dt = datetime(1900, 1, 1)
    else:
        start_dt = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    else:
        end_dt = today.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    loan_filter_conditions = [
        Department.id == department_id,
        Loan.issued_at >= start_dt,
        Loan.issued_at < end_dt,
        Loan.status.in_((LoanStatus.BORROWED, LoanStatus.OVERDUE, LoanStatus.RETURNED)),
    ]
    if category_id:
        loan_filter_conditions.append(Book.category_id == category_id)
    if user_type:
        loan_filter_conditions.append(User.role == RoleType(user_type))

    dept = db.session.get(Department, department_id)
    if not dept:
        return None

    kpis = {}
    comparisons = {}
    charts = {}
    rankings = {}
    suggestions_data = {}
    copy_filter_conditions = [Department.id == department_id]
    if category_id:
        copy_filter_conditions.append(Book.category_id == category_id)
    user_type_conditions = [User.role == RoleType(user_type)] if user_type else []

    dept_books_count = db.session.query(func.count(func.distinct(Book.id))).join(
        Book.departments
    ).filter(*copy_filter_conditions).scalar()
    kpis["department_books"] = dept_books_count or 0

    copy_statuses = db.session.query(BookCopy.status, func.count(BookCopy.id)).join(
        Book, BookCopy.book_id == Book.id
    ).join(Book.departments).filter(*copy_filter_conditions).group_by(BookCopy.status).all()

    status_map = {status.value: count for status, count in copy_statuses}
    kpis["available_copies"] = status_map.get("AVAILABLE", 0)
    kpis["currently_borrowed"] = status_map.get("BORROWED", 0)
    kpis["overdue_books"] = 0

    overdue_count = db.session.query(func.count(Loan.id)).join(
        BookCopy, Loan.book_copy_id == BookCopy.id
    ).join(Book, BookCopy.book_id == Book.id
    ).join(Book.departments).join(User, Loan.user_id == User.id).filter(
        *copy_filter_conditions, Loan.status == LoanStatus.OVERDUE,
        Loan.due_at >= start_dt, Loan.due_at < end_dt, *user_type_conditions,
    ).scalar()
    kpis["overdue_books"] = overdue_count or 0

    active_students = db.session.query(func.count(func.distinct(User.id))).filter(
        User.department_id == department_id,
        User.role == RoleType.STUDENT,
        User.is_active == True,
        *user_type_conditions,
    ).scalar()
    kpis["active_students"] = active_students or 0

    active_faculty = db.session.query(func.count(func.distinct(User.id))).filter(
        User.department_id == department_id,
        User.role == RoleType.FACULTY,
        User.is_active == True,
        *user_type_conditions,
    ).scalar()
    kpis["active_faculty"] = active_faculty or 0

    pending_suggestions_query = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id)
    pending_suggestions = filter_department_suggestions(
        pending_suggestions_query, filters, start_dt, end_dt
    ).filter(Suggestion.status == SuggestionStatus.UNDER_REVIEW).count()
    kpis["pending_suggestions"] = pending_suggestions or 0

    votes_query = db.session.query(SuggestionVote).join(
        Suggestion, SuggestionVote.suggestion_id == Suggestion.id
    ).join(User, Suggestion.submitted_by == User.id).filter(User.department_id == department_id)
    total_votes = filter_department_suggestions(votes_query, filters, start_dt, end_dt).count()
    kpis["suggestion_support"] = total_votes or 0



    monthly_borrowing = db.session.query(
        month_bucket(Loan.issued_at).label('month'),
        func.count(Loan.id).label('total_loans'),
        func.count(Loan.id).filter(User.role == RoleType.STUDENT).label('student_loans'),
        func.count(Loan.id).filter(User.role == RoleType.FACULTY).label('faculty_loans')
    ).join(User, Loan.user_id == User.id).join(
        BookCopy, Loan.book_copy_id == BookCopy.id
    ).join(Book, BookCopy.book_id == Book.id).join(
        Book.departments
    ).filter(*loan_filter_conditions).group_by('month').order_by('month').all()

    charts["monthly_borrowing_trend"] = [
        {"month": month_label(row.month), "total_loans": row.total_loans} for row in monthly_borrowing
    ]

    borrowing_by_category = db.session.query(
        Category.name.label('category_name'),
        func.count(Loan.id).label('borrow_count')
    ).join(
        User, Loan.user_id == User.id
    ).join(
        BookCopy, Loan.book_copy_id == BookCopy.id
    ).join(
        Book, BookCopy.book_id == Book.id
    ).join(
        Book.departments
    ).join(
        Category, Book.category_id == Category.id
    ).filter(*loan_filter_conditions).group_by(Category.name).order_by(func.count(Loan.id).desc()).all()

    charts["borrowing_by_category"] = [
        {"category_name": row.category_name, "borrow_count": row.borrow_count} for row in borrowing_by_category
    ]

    student_vs_faculty = db.session.query(
        month_bucket(Loan.issued_at).label('month'),
        func.count(Loan.id).filter(User.role == RoleType.STUDENT).label('students'),
        func.count(Loan.id).filter(User.role == RoleType.FACULTY).label('faculty')
    ).join(User, Loan.user_id == User.id).join(
        BookCopy, Loan.book_copy_id == BookCopy.id
    ).join(Book, BookCopy.book_id == Book.id).join(
        Book.departments
    ).filter(*loan_filter_conditions).group_by('month').order_by('month').all()

    charts["student_vs_faculty_borrowing"] = [
        {"period": month_label(row.month), "students": row.students, "faculty": row.faculty} for row in student_vs_faculty
    ]

    utilization = db.session.query(
        month_bucket(Loan.issued_at).label('month'),
        (func.count(Loan.id) * 100.0 / func.nullif(kpis["department_books"], 0)).label('utilization_rate')
    ).join(BookCopy, Loan.book_copy_id == BookCopy.id).join(
        Book, BookCopy.book_id == Book.id
    ).join(Book.departments).join(User, Loan.user_id == User.id).filter(*loan_filter_conditions).group_by('month').order_by('month').all()

    charts["department_book_utilization"] = [
        {"period": month_label(row.month), "utilization_rate": round(float(row.utilization_rate or 0), 1)} for row in utilization
    ]

    charts["book_copy_status"] = [
        {"status": status.value if hasattr(status, 'value') else str(status), "count": count} for status, count in copy_statuses
    ]

    suggestion_demand_query = db.session.query(
        Category.name.label('category_name'),
        func.count(Suggestion.id).label('suggestion_count')
    ).join(
        User, Suggestion.submitted_by == User.id
    ).outerjoin(
        Category, Suggestion.category_id == Category.id
    ).filter(User.department_id == department_id)
    suggestion_demand = filter_department_suggestions(
        suggestion_demand_query, filters, start_dt, end_dt
    ).group_by(Category.name).order_by(func.count(Suggestion.id).desc()).all()

    charts["suggestion_demand_by_category"] = [
        {"category_name": row.category_name or "Uncategorized", "suggestion_count": row.suggestion_count} for row in suggestion_demand
    ]

    overdue_trend = db.session.query(
        month_bucket(Loan.due_at).label('month'),
        func.count(Loan.id).label('overdue_count')
    ).join(BookCopy, Loan.book_copy_id == BookCopy.id).join(
        Book, BookCopy.book_id == Book.id
    ).join(Book.departments).join(User, Loan.user_id == User.id).filter(
        *copy_filter_conditions,
        Loan.status == LoanStatus.OVERDUE,
        Loan.due_at >= start_dt,
        Loan.due_at < end_dt,
        *user_type_conditions,
    ).group_by('month').order_by('month').all()

    charts["overdue_trend"] = [
        {"period": month_label(row.month), "overdue_count": row.overdue_count} for row in overdue_trend
    ]

    top_borrowed = db.session.query(
        Book.title, func.count(Loan.id).label('borrow_count')
    ).join(BookCopy, Book.id == BookCopy.book_id).join(
        Loan, BookCopy.id == Loan.book_copy_id
    ).join(Book.departments).join(User, Loan.user_id == User.id).filter(*loan_filter_conditions).group_by(Book.id, Book.title).order_by(func.count(Loan.id).desc()).limit(5).all()

    rankings["top_borrowed_books"] = [
        {"title": row.title, "author": "", "borrow_count": row.borrow_count} for row in top_borrowed
    ]

    top_suggested_query = db.session.query(
        Suggestion.title,
        func.count(SuggestionVote.suggestion_id).label('vote_count'),
        func.max(Suggestion.created_at).label('created_at')
    ).join(User, Suggestion.submitted_by == User.id).outerjoin(
        SuggestionVote, Suggestion.id == SuggestionVote.suggestion_id
    ).filter(User.department_id == department_id)
    top_suggested = filter_department_suggestions(
        top_suggested_query, filters, start_dt, end_dt
    ).group_by(Suggestion.id, Suggestion.title).order_by(
        func.count(SuggestionVote.suggestion_id).desc(), Suggestion.created_at.asc(), Suggestion.title.asc()
    ).limit(5).all()

    rankings["top_suggested_books"] = [
        {"title": row.title, "vote_count": row.vote_count, "created_at": row.created_at.isoformat() if row.created_at else None} for row in top_suggested
    ]

    student_suggestions_query = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id)
    student_suggestions = filter_department_suggestions(
        student_suggestions_query, filters, start_dt, end_dt
    ).filter(User.role == RoleType.STUDENT).count()
    faculty_suggestions_query = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id)
    faculty_suggestions = filter_department_suggestions(
        faculty_suggestions_query, filters, start_dt, end_dt
    ).filter(User.role == RoleType.FACULTY).count()

    suggestions_data["student_vs_faculty"] = {
        "student": student_suggestions or 0,
        "faculty": faculty_suggestions or 0
    }

    status_distribution_query = db.session.query(
        Suggestion.status, func.count(Suggestion.id)
    ).join(User, Suggestion.submitted_by == User.id).filter(User.department_id == department_id)
    status_dist = filter_department_suggestions(
        status_distribution_query, filters, start_dt, end_dt
    ).group_by(Suggestion.status).all()

    suggestions_data["status_distribution"] = {status.value: count for status, count in status_dist}

    suggestions_query = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id)
    suggestions_query = filter_department_suggestions(suggestions_query, filters, start_dt, end_dt)
    suggestions_query = suggestions_query.order_by(Suggestion.created_at.desc()).limit(20)

    suggestions_list = []
    for s in suggestions_query.all():
        vote_count = db.session.query(func.count(SuggestionVote.suggestion_id)).filter(
            SuggestionVote.suggestion_id == s.id
        ).scalar()
        suggestions_list.append({
            "id": str(s.id),
            "title": s.title,
            "author": s.author or "",
            "requester": s.submitted_by_user.name,
            "requester_type": s.submitted_by_user.role.value,
            "department": dept.name,
            "reason": s.reason.value,
            "votes": vote_count or 0,
            "status": s.status.value,
            "created_at": s.created_at.isoformat()
        })

    suggestions_data["items"] = suggestions_list

    recent_suggestions_query = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id)
    recent_suggestions = filter_department_suggestions(
        recent_suggestions_query, filters, start_dt, end_dt
    ).order_by(Suggestion.created_at.desc()).limit(5).all()

    recent_list = []
    for s in recent_suggestions:
        vote_count = db.session.query(func.count(SuggestionVote.suggestion_id)).filter(
            SuggestionVote.suggestion_id == s.id
        ).scalar()
        recent_list.append({
            "id": str(s.id),
            "title": s.title,
            "requester_type": s.submitted_by_user.role.value,
            "created_at": s.created_at.isoformat(),
            "votes": vote_count or 0
        })

    department_categories = db.session.query(Category.id, Category.name).join(
        Book, Category.id == Book.category_id
    ).join(Book.departments).filter(
        Department.id == department_id
    ).distinct().order_by(Category.name).all()

    return {
        "scope": {"id": str(dept.id), "name": dept.name},
        "categories": [{"category_id": str(category_id), "category_name": name} for category_id, name in department_categories],
        "summary": kpis,
        "comparisons": comparisons,
        "charts": charts,
        "rankings": rankings,
        "suggestions": suggestions_data,
        "borrowing_trend": charts["monthly_borrowing_trend"],
        "borrowing_by_category": charts["borrowing_by_category"],
        "student_vs_faculty": charts["student_vs_faculty_borrowing"],
        "book_utilization": charts["department_book_utilization"],
        "copy_status": charts["book_copy_status"],
        "suggestion_demand": charts["suggestion_demand_by_category"],
        "top_books": rankings["top_suggested_books"],
        "recent_suggestions": recent_list,
        "meta": {
            "source": f"{db.engine.dialect.name.upper()} Database",
            "is_demo": False,
            "generated_at": datetime.now().astimezone().isoformat()
        }
    }


@app.route("/api/health", methods=["GET"])
def health():
    try:
        db.session.execute(text("SELECT 1"))
        inspector = inspect(db.engine)
        required_tables = {"departments", "users", "books", "book_copies", "loans", "suggestions", "suggestion_votes"}
        missing = sorted(required_tables - set(inspector.get_table_names()))
        if missing:
            return jsonify({
                "status": "error",
                "error": {
                    "code": "DATABASE_SCHEMA_INCOMPLETE",
                    "message": f"Database is reachable but required tables are missing: {', '.join(missing)}.",
                },
            }), 503
        return jsonify({
            "status": "success",
            "message": "LibSphere backend is running",
            "database": "ok",
        }), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Health check could not reach the database")
        return jsonify({
            "status": "error",
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "The backend is running but its database is unavailable.",
            },
        }), 503


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error": {"code": "INVALID_REQUEST", "message": "Request body required"}}), 400

    if app.config.get("APP_ENV") == "testing":
        name_key = canonicalize_name(data.get("name"))
        user_id_key = canonicalize_user_id(data.get("user_id"))
        requested_role = canonicalize_role(data.get("role"))
        public_roles = {"STUDENT", "FACULTY", "DEPARTMENT", "LIBRARIAN"}
        if not name_key or not user_id_key or requested_role not in public_roles:
            return jsonify({"status": "error", "error": {
                "code": "INVALID_IDENTITY", "message": "Name, user ID, and a valid testing role are required."
            }}), 401
        role = RoleType(requested_role)
        identifier_field = User.enrollment_id if role == RoleType.STUDENT else User.employee_id
        candidates = db.session.query(User).filter(
            User.role == role,
            User.is_active.is_(True),
            User.email.like("%@libsphere.test"),
        ).all()
        user = next((candidate for candidate in candidates
                     if canonicalize_name(candidate.name) == name_key
                     and canonicalize_user_id(getattr(candidate, identifier_field.key)) == user_id_key), None)
        if not user:
            return jsonify({"status": "error", "error": {
                "code": "INVALID_IDENTITY", "message": "Name, user ID, and role did not match an active local testing account."
            }}), 401
    else:
        email = str(data.get("email", "")).strip()
        password = data.get("password")
        if not email or not isinstance(password, str) or not password:
            return jsonify({"status": "error", "error": {
                "code": "MISSING_CREDENTIALS", "message": "Email and password are required."
            }}), 400
        user = db.session.query(User).filter(
            User.email == email,
            User.is_active.is_(True),
        ).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"status": "error", "error": {
                "code": "INVALID_CREDENTIALS", "message": "Invalid email or password."
            }}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "status": "success",
        "data": {
            "access_token": access_token,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
                "department_id": str(user.department_id) if user.department_id else None
            }
        }
    }), 200


@app.route("/api/reports/department/dashboard", methods=["GET"])
@jwt_required()
def department_dashboard():
    try:
        user = authenticated_active_user()

        if not user:
            return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401

        if user.role not in [RoleType.DEPARTMENT, RoleType.ADMIN, RoleType.LIBRARIAN]:
            return jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}), 403

        department_id = user.department_id
        if user.role == RoleType.ADMIN or user.role == RoleType.LIBRARIAN:
            dept_id_param = request.args.get("department_id")
            if dept_id_param:
                try:
                    department_id = dept_id_param
                except ValueError:
                    pass

        if not department_id:
            return jsonify({"status": "error", "error": {"code": "NO_DEPARTMENT", "message": "User has no associated department"}}), 400

        filters = validate_filters()
        data = get_department_dashboard_data(department_id, filters)

        if not data:
            return jsonify({"status": "error", "error": {"code": "DEPARTMENT_NOT_FOUND", "message": "Department not found"}}), 404

        return jsonify({"status": "success", "data": data}), 200

    except ValueError as e:
        return jsonify({"status": "error", "error": {"code": "INVALID_REPORT_FILTER", "message": str(e)}}), 422
    except Exception:
        app.logger.exception("Dashboard generation failed")
        return jsonify({"status": "error", "error": {"code": "REPORT_GENERATION_FAILED", "message": "Unable to generate department dashboard report."}}), 500


@app.route("/api/reports/librarian/dashboard", methods=["GET"])
@jwt_required()
def librarian_dashboard():
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {
            "code": "ACCOUNT_DISABLED", "message": "Active account required."
        }}), 401
    if user.role != RoleType.LIBRARIAN:
        return jsonify({"status": "error", "error": {
            "code": "FORBIDDEN", "message": "Insufficient permissions"
        }}), 403

    summary = {
        "total_books": db.session.query(func.count(Book.id)).scalar() or 0,
        "total_copies": db.session.query(func.count(BookCopy.id)).scalar() or 0,
        "available_copies": db.session.query(func.count(BookCopy.id)).filter(
            BookCopy.status == CopyStatus.AVAILABLE
        ).scalar() or 0,
        "borrowed_copies": db.session.query(func.count(BookCopy.id)).filter(
            BookCopy.status == CopyStatus.BORROWED
        ).scalar() or 0,
        "overdue_loans": db.session.query(func.count(Loan.id)).filter(
            Loan.status == LoanStatus.OVERDUE
        ).scalar() or 0,
        "suggestion_votes": db.session.query(func.count(SuggestionVote.suggestion_id)).scalar() or 0,
    }
    return jsonify({"status": "success", "data": {
        "summary": summary,
        "meta": {"source": f"{db.engine.dialect.name.upper()} Database"},
    }}), 200


@app.route("/api/librarian/users", methods=["GET"])
@jwt_required()
def librarian_users():
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {
            "code": "ACCOUNT_DISABLED", "message": "Active account required."
        }}), 401
    if user.role not in {RoleType.LIBRARIAN, RoleType.ADMIN}:
        return jsonify({"status": "error", "error": {
            "code": "FORBIDDEN", "message": "Insufficient permissions"
        }}), 403

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": {
            "code": "INVALID_PAGINATION", "message": "page and per_page must be integers."
        }}), 422
    if page < 1 or per_page < 1 or per_page > 100:
        return jsonify({"status": "error", "error": {
            "code": "INVALID_PAGINATION", "message": "page must be positive and per_page must be between 1 and 100."
        }}), 422

    search = (request.args.get("q") or "").strip()
    if len(search) > 200:
        return jsonify({"status": "error", "error": {
            "code": "INVALID_FILTER", "message": "Search is too long."
        }}), 422

    role_filter = (request.args.get("role") or "").strip().upper()
    if role_filter:
        try:
            role_filter = RoleType(role_filter).value
        except ValueError:
            return jsonify({"status": "error", "error": {
                "code": "INVALID_FILTER", "message": "Unknown user role."
            }}), 422

    department_id = (request.args.get("department_id") or "").strip()
    if department_id:
        try:
            department_id = str(uuid.UUID(department_id))
        except (TypeError, ValueError):
            return jsonify({"status": "error", "error": {
                "code": "INVALID_FILTER", "message": "Invalid department ID."
            }}), 422
        if not db.session.get(Department, department_id):
            return jsonify({"status": "error", "error": {
                "code": "INVALID_FILTER", "message": "Unknown department ID."
            }}), 422

    account_status = (request.args.get("account_status") or "").strip().lower()
    if account_status not in {"", "enabled", "disabled"}:
        return jsonify({"status": "error", "error": {
            "code": "INVALID_FILTER", "message": "account_status must be enabled or disabled."
        }}), 422

    sort_key = (request.args.get("sort") or "name").strip().lower()
    sort_columns = {
        "name": User.name,
        "user_id": case((User.role == RoleType.STUDENT, User.enrollment_id), else_=User.employee_id),
        "role": User.role,
        "department": Department.name,
        "status": User.is_active,
        "created_at": User.created_at,
    }
    if sort_key not in sort_columns:
        return jsonify({"status": "error", "error": {
            "code": "INVALID_SORT", "message": "Unsupported user sort field."
        }}), 422
    direction = (request.args.get("direction") or "asc").strip().lower()
    if direction not in {"asc", "desc"}:
        return jsonify({"status": "error", "error": {
            "code": "INVALID_SORT", "message": "direction must be asc or desc."
        }}), 422

    query = db.session.query(User).outerjoin(Department, User.department_id == Department.id)
    if role_filter:
        query = query.filter(User.role == RoleType(role_filter))
    if department_id:
        query = query.filter(User.department_id == department_id)
    if account_status:
        query = query.filter(User.is_active.is_(account_status == "enabled"))
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            User.name.ilike(term), User.enrollment_id.ilike(term), User.employee_id.ilike(term),
        ))
    sort_column = sort_columns[sort_key]
    query = query.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), User.id.asc()
    )
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    role_summary = {role.value: {"total": 0, "enabled": 0, "disabled": 0} for role in RoleType}
    for role, enabled, count in db.session.query(User.role, User.is_active, func.count(User.id)).group_by(
        User.role, User.is_active
    ).all():
        bucket = role_summary[role.value]
        bucket["total"] += count
        bucket["enabled" if enabled else "disabled"] = count
    total_accounts = sum(row["total"] for row in role_summary.values())
    enabled_accounts = sum(row["enabled"] for row in role_summary.values())
    departments = db.session.query(Department).order_by(Department.name).all()

    items = []
    for record in rows:
        identifier = record.enrollment_id if record.role == RoleType.STUDENT else record.employee_id
        items.append({
            "name": record.name,
            "user_id": identifier,
            "role": record.role.value,
            "department": ({
                "id": str(record.department.id), "code": record.department.code,
                "name": record.department.name,
            } if record.department else None),
            "is_active": bool(record.is_active),
        })

    return jsonify({"status": "success", "data": {
        "items": items,
        "pagination": {
            "page": page, "per_page": per_page, "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
        "summary": {
            "total_accounts": total_accounts,
            "enabled_accounts": enabled_accounts,
            "disabled_accounts": total_accounts - enabled_accounts,
            "by_role": role_summary,
        },
        "departments": [{"id": str(dept.id), "code": dept.code, "name": dept.name} for dept in departments],
    }}), 200


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"status": "error", "error": {"code": "USER_NOT_FOUND", "message": "User not found"}}), 404
    if not user.is_active:
        return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "This account is inactive."}}), 401

    return jsonify({
        "status": "success",
        "data": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "department_id": str(user.department_id) if user.department_id else None
        }
    }), 200




@app.route("/api/books/search", methods=["GET"])
@jwt_required()
def search_books():
    try:
        user = authenticated_active_user()
        if not user:
            return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
        query = request.args.get("q", "").strip()
        if len(query) > 200:
            return jsonify({"status": "error", "error": {"code": "INVALID_FILTER", "message": "Search is too long."}}), 400
        category_id = (request.args.get("category_id") or "").strip()
        availability = request.args.get("availability", "").strip().lower()
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 20))
        except (TypeError, ValueError):
            return jsonify({"status": "error", "error": {"code": "INVALID_PAGINATION", "message": "page and per_page must be integers."}}), 400
        if page < 1 or per_page < 1 or per_page > 100:
            return jsonify({"status": "error", "error": {"code": "INVALID_PAGINATION", "message": "page must be positive and per_page must be between 1 and 100."}}), 400
        if availability not in {"", "available", "unavailable"}:
            return jsonify({"status": "error", "error": {"code": "INVALID_FILTER", "message": "availability must be available or unavailable."}}), 400
        if category_id:
            try:
                category_id = str(uuid.UUID(category_id))
            except (TypeError, ValueError):
                return jsonify({"status": "error", "error": {"code": "INVALID_FILTER", "message": "category_id is invalid."}}), 400
            if db.session.get(Category, category_id) is None:
                return jsonify({"status": "error", "error": {"code": "INVALID_FILTER", "message": "category_id is invalid."}}), 400

        q = db.session.query(Book)
        if query:
            q = q.filter(
                (Book.title.ilike(f"%{query}%")) |
                (Book.authors.any(Author.name.ilike(f"%{query}%"))) |
                (Book.isbn.ilike(f"%{query}%"))
            )
        if category_id:
            q = q.filter(Book.category_id == category_id)
        if availability == "available":
            q = q.filter(Book.copies.any(BookCopy.status == CopyStatus.AVAILABLE))
        elif availability == "unavailable":
            q = q.filter(~Book.copies.any(BookCopy.status == CopyStatus.AVAILABLE))

        q = q.distinct().order_by(Book.title.asc(), Book.id.asc())
        total = q.count()
        books = q.offset((page - 1) * per_page).limit(per_page).all()

        results = []
        for book in books:
            copies = db.session.query(BookCopy).filter(BookCopy.book_id == book.id).order_by(BookCopy.id).all()
            avail = sum(1 for copy in copies if copy.status == CopyStatus.AVAILABLE)
            results.append({
                "id": str(book.id),
                "title": book.title,
                "author": ", ".join(author.name for author in book.authors) or "",
                "isbn": book.isbn,
                "category": book.category.name if book.category else "",
                "available": avail,
                "total": len(copies),
                "rack": copies[0].rack if copies else "",
            })

        return jsonify({
            "status": "success",
            "data": {
                "items": results,
                "total": total,
                "page": page,
                "per_page": per_page,
            },
        }), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Book search failed")
        return jsonify({"status": "error", "error": {"code": "SEARCH_FAILED", "message": "Unable to search the catalogue."}}), 500


def serialize_loan_record(loan):
    issued = loan.status in {LoanStatus.BORROWED, LoanStatus.OVERDUE, LoanStatus.RETURNED}
    book = loan.book_copy.book
    return {
        "id": str(loan.id),
        "book_id": str(book.id),
        "book_title": book.title,
        "book_author": ", ".join(author.name for author in book.authors) or "",
        "requester_id": str(loan.user_id),
        "requester_name": loan.user.name,
        "requester_role": loan.user.role.value,
        "request_submitted_at": loan.created_at.isoformat() if loan.created_at else None,
        "issued_at": loan.issued_at.isoformat() if issued and loan.issued_at else None,
        "due_at": loan.due_at.isoformat() if issued and loan.due_at else None,
        "returned_at": loan.returned_at.isoformat() if loan.returned_at else None,
        "status": loan.status.value,
        "decision": loan.status.value if loan.status in {LoanStatus.APPROVED, LoanStatus.REJECTED} else None,
        "rack": loan.book_copy.rack,
        "shelf": loan.book_copy.shelf,
    }


def authenticated_active_user():
    user = db.session.get(User, get_jwt_identity())
    return user if user and user.is_active else None


def add_loan_notification(user, title, message):
    db.session.add(Notification(
        user_id=user.id, type=NotificationType.SYSTEM, title=title, message=message,
    ))


def audit_loan_event(actor, action, loan):
    db.session.add(AuditLog(
        actor_user_id=actor.id, action=action, entity_type="loan", entity_id=loan.id,
        details={"loan_status": loan.status.value, "book_copy_id": str(loan.book_copy_id)},
    ))


@app.route("/api/users/me/loans", methods=["GET"])
@jwt_required()
def my_loans():
    try:
        user = authenticated_active_user()
        if not user:
            return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
        loans = db.session.query(Loan).filter(Loan.user_id == user.id).order_by(Loan.created_at.desc()).all()
        return jsonify({"status": "success", "data": [serialize_loan_record(loan) for loan in loans]}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("My loans failed")
        return jsonify({"status": "error", "error": {"code": "LOANS_FAILED", "message": "Unable to load your borrowing history."}}), 500


@app.route("/api/users/me/loans/requests", methods=["POST"])
@jwt_required()
def request_book_loan():
    try:
        user = authenticated_active_user()
        if not user:
            return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
        if user.role not in {RoleType.STUDENT, RoleType.FACULTY}:
            return jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Only students and faculty may request books."}}), 403
        payload = request.get_json(silent=True)
        book_id = payload.get("book_id") if isinstance(payload, dict) else None
        if not isinstance(book_id, str) or not book_id.strip():
            return jsonify({"status": "error", "error": {"code": "INVALID_INPUT", "message": "book_id is required."}}), 400
        book = db.session.get(Book, book_id)
        if not book:
            return jsonify({"status": "error", "error": {"code": "BOOK_NOT_FOUND", "message": "Book was not found."}}), 404

        active_statuses = (LoanStatus.REQUESTED, LoanStatus.APPROVED, LoanStatus.BORROWED, LoanStatus.OVERDUE)
        duplicate = db.session.query(Loan).join(BookCopy).filter(
            Loan.user_id == user.id, BookCopy.book_id == book.id, Loan.status.in_(active_statuses)
        ).first()
        if duplicate:
            return jsonify({"status": "error", "error": {"code": "DUPLICATE_REQUEST", "message": "You already have an active request or loan for this book."}}), 409

        copy = db.session.query(BookCopy).filter(
            BookCopy.book_id == book.id, BookCopy.status == CopyStatus.AVAILABLE
        ).order_by(BookCopy.accession_number).with_for_update().first()
        if not copy:
            return jsonify({"status": "error", "error": {"code": "NO_COPY_AVAILABLE", "message": "No available copy can be requested right now."}}), 409
        now = datetime.now()
        copy.status = CopyStatus.RESERVED
        loan = Loan(
            user_id=user.id, book_copy_id=copy.id, issued_at=now,
            due_at=now + timedelta(days=14), status=LoanStatus.REQUESTED,
        )
        db.session.add(loan)
        try:
            db.session.flush()
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify({"status": "error", "error": {"code": "COPY_CONFLICT", "message": "That copy was just requested. Refresh availability and retry."}}), 409
        for librarian in db.session.query(User).filter(
            User.role == RoleType.LIBRARIAN, User.is_active.is_(True)
        ).all():
            add_loan_notification(librarian, "New borrowing request", f"{user.name} requested {book.title}.")
        audit_loan_event(user, "LOAN_REQUESTED", loan)
        db.session.commit()
        db.session.refresh(loan)
        return jsonify({"status": "success", "data": serialize_loan_record(loan)}), 201
    except Exception:
        db.session.rollback()
        app.logger.exception("Book request failed")
        return jsonify({"status": "error", "error": {"code": "REQUEST_FAILED", "message": "Unable to submit the borrowing request."}}), 500


@app.route("/api/librarian/loan-requests", methods=["GET"])
@jwt_required()
def librarian_loan_requests():
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    if user.role not in {RoleType.LIBRARIAN, RoleType.ADMIN}:
        return jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Librarian access required."}}), 403
    try:
        pending = db.session.query(Loan).filter(Loan.status.in_((LoanStatus.REQUESTED, LoanStatus.APPROVED))).order_by(Loan.created_at.asc()).all()
        return jsonify({"status": "success", "data": [serialize_loan_record(loan) for loan in pending]}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Librarian request queue failed")
        return jsonify({"status": "error", "error": {"code": "REQUEST_QUEUE_FAILED", "message": "Unable to load borrowing requests."}}), 500


@app.route("/api/librarian/loan-requests/<loan_id>/review", methods=["POST"])
@jwt_required()
def review_loan_request(loan_id):
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    if user.role not in {RoleType.LIBRARIAN, RoleType.ADMIN}:
        return jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Librarian access required."}}), 403
    payload = request.get_json(silent=True)
    decision = str(payload.get("decision", "")).strip().upper() if isinstance(payload, dict) else ""
    if decision not in {"APPROVED", "REJECTED"}:
        return jsonify({"status": "error", "error": {"code": "INVALID_DECISION", "message": "decision must be APPROVED or REJECTED."}}), 400
    try:
        loan = db.session.get(Loan, loan_id)
        if not loan:
            return jsonify({"status": "error", "error": {"code": "LOAN_NOT_FOUND", "message": "Request was not found."}}), 404
        if loan.status != LoanStatus.REQUESTED:
            return jsonify({"status": "error", "error": {"code": "INVALID_STATE", "message": "Only pending requests can be reviewed."}}), 409
        loan.status = LoanStatus(decision)
        loan.issued_by = user.id
        if loan.status == LoanStatus.REJECTED:
            loan.book_copy.status = CopyStatus.AVAILABLE
        add_loan_notification(
            loan.user, "Borrowing request updated",
            f"Your request for {loan.book_copy.book.title} was {decision.casefold()}.",
        )
        audit_loan_event(user, f"LOAN_{decision}", loan)
        db.session.commit()
        db.session.refresh(loan)
        return jsonify({"status": "success", "data": serialize_loan_record(loan)}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Borrowing request review failed")
        return jsonify({"status": "error", "error": {"code": "REVIEW_FAILED", "message": "Unable to review this request."}}), 500


@app.route("/api/librarian/loan-requests/<loan_id>/issue", methods=["POST"])
@jwt_required()
def issue_approved_loan(loan_id):
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    if user.role not in {RoleType.LIBRARIAN, RoleType.ADMIN}:
        return jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Librarian access required."}}), 403
    try:
        loan = db.session.get(Loan, loan_id)
        if not loan:
            return jsonify({"status": "error", "error": {"code": "LOAN_NOT_FOUND", "message": "Request was not found."}}), 404
        if loan.status != LoanStatus.APPROVED or loan.book_copy.status != CopyStatus.RESERVED:
            return jsonify({"status": "error", "error": {"code": "INVALID_STATE", "message": "Only an approved request with a reserved copy can be issued."}}), 409
        loan.status = LoanStatus.BORROWED
        loan.issued_at = datetime.now()
        loan.due_at = loan.issued_at + timedelta(days=14)
        loan.issued_by = user.id
        loan.book_copy.status = CopyStatus.BORROWED
        add_loan_notification(loan.user, "Book issued", f"{loan.book_copy.book.title} is issued; due {loan.due_at.date().isoformat()}.")
        audit_loan_event(user, "LOAN_ISSUED", loan)
        db.session.commit()
        db.session.refresh(loan)
        return jsonify({"status": "success", "data": serialize_loan_record(loan)}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Loan issue failed")
        return jsonify({"status": "error", "error": {"code": "ISSUE_FAILED", "message": "Unable to issue this loan."}}), 500


@app.route("/api/users/me/loans/<loan_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_loan_request(loan_id):
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    try:
        loan = db.session.get(Loan, loan_id)
        if not loan or loan.user_id != user.id:
            return jsonify({"status": "error", "error": {"code": "LOAN_NOT_FOUND", "message": "Request was not found."}}), 404
        if loan.status not in {LoanStatus.REQUESTED, LoanStatus.APPROVED}:
            return jsonify({"status": "error", "error": {"code": "INVALID_STATE", "message": "This request can no longer be cancelled."}}), 409
        loan.status = LoanStatus.CANCELLED
        loan.book_copy.status = CopyStatus.AVAILABLE
        audit_loan_event(user, "LOAN_CANCELLED", loan)
        db.session.commit()
        db.session.refresh(loan)
        return jsonify({"status": "success", "data": serialize_loan_record(loan)}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Loan cancellation failed")
        return jsonify({"status": "error", "error": {"code": "CANCEL_FAILED", "message": "Unable to cancel this request."}}), 500


@app.route("/api/users/me/suggestions", methods=["GET"])
@jwt_required()
def my_suggestions():
    try:
        user = authenticated_active_user()
        if not user:
            return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
        suggestions = db.session.query(Suggestion).order_by(Suggestion.created_at.desc(), Suggestion.id.asc()).all()

        results = []
        for suggestion in suggestions:
            vote_count = db.session.query(func.count(SuggestionVote.user_id)).filter(
                SuggestionVote.suggestion_id == suggestion.id
            ).scalar() or 0
            voted_by_me = db.session.query(SuggestionVote.suggestion_id).filter(
                SuggestionVote.suggestion_id == suggestion.id,
                SuggestionVote.user_id == user.id,
            ).first() is not None
            results.append({
                "id": str(suggestion.id),
                "title": suggestion.title,
                "author": suggestion.author or "",
                "reason": suggestion.reason.value,
                "status": suggestion.status.value,
                "votes": vote_count,
                "voted_by_me": voted_by_me,
                "is_own": suggestion.submitted_by == user.id,
                "created_at": suggestion.created_at.isoformat(),
            })

        return jsonify({"status": "success", "data": results}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("My suggestions failed")
        return jsonify({"status": "error", "error": {"code": "SUGGESTIONS_FAILED", "message": "Unable to load suggestions."}}), 500


@app.route("/api/suggestions", methods=["POST"])
@jwt_required()
def create_suggestion():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        title = data.get("title", "").strip()
        author = data.get("author", "").strip()
        category_id = data.get("category_id")
        justification = data.get("justification", "").strip()
        reason = data.get("reason", "COURSE_REQUIREMENT")

        if not title or not justification:
            return jsonify({"status": "error", "error": {"code": "INVALID_INPUT", "message": "Title and justification required"}}), 400

        suggestion = Suggestion(
            title=title,
            author=author or None,
            category_id=category_id,
            justification=justification,
            reason=SuggestionReason(reason),
            submitted_by=current_user_id
        )
        db.session.add(suggestion)
        db.session.commit()

        return jsonify({
            "status": "success",
            "data": {"id": str(suggestion.id), "title": suggestion.title}
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.exception("Create suggestion failed")
        return jsonify({"status": "error", "error": {"code": "CREATE_FAILED", "message": str(e)}}), 500


@app.route("/api/suggestions/<suggestion_id>/vote", methods=["POST"])
@jwt_required()
def vote_suggestion(suggestion_id):
    try:
        user = authenticated_active_user()
        if not user:
            return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
        suggestion = db.session.get(Suggestion, suggestion_id)
        if not suggestion:
            return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Suggestion not found."}}), 404

        existing = db.session.query(SuggestionVote).filter(
            SuggestionVote.suggestion_id == suggestion.id,
            SuggestionVote.user_id == user.id,
        ).first()
        if existing:
            vote_count = db.session.query(func.count(SuggestionVote.user_id)).filter(
                SuggestionVote.suggestion_id == suggestion.id
            ).scalar() or 0
            return jsonify({"status": "success", "data": {"voted": True, "vote_count": vote_count}}), 200

        db.session.add(SuggestionVote(suggestion_id=suggestion.id, user_id=user.id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            vote_count = db.session.query(func.count(SuggestionVote.user_id)).filter(
                SuggestionVote.suggestion_id == suggestion.id
            ).scalar() or 0
            return jsonify({"status": "success", "data": {"voted": True, "vote_count": vote_count}}), 200

        vote_count = db.session.query(func.count(SuggestionVote.user_id)).filter(
            SuggestionVote.suggestion_id == suggestion.id
        ).scalar() or 0
        return jsonify({"status": "success", "data": {"voted": True, "vote_count": vote_count}}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Vote failed")
        return jsonify({"status": "error", "error": {"code": "VOTE_FAILED", "message": "Unable to submit this vote."}}), 500


@app.route("/api/librarian/catalogue", methods=["GET"])
@jwt_required()
def librarian_catalogue():
    user = authenticated_active_user()
    if not user:
        return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    if user.role not in {RoleType.LIBRARIAN, RoleType.ADMIN}:
        return jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Librarian access required."}}), 403
    try:
        page, per_page = int(request.args.get("page", 1)), int(request.args.get("per_page", 20))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": {"code": "INVALID_PAGINATION", "message": "page and per_page must be integers."}}), 422
    if page < 1 or not 1 <= per_page <= 100:
        return jsonify({"status": "error", "error": {"code": "INVALID_PAGINATION", "message": "page must be positive; per_page must be 1-100."}}), 422
    term = (request.args.get("q") or "").strip()
    if len(term) > 200:
        return jsonify({"status": "error", "error": {"code": "INVALID_FILTER", "message": "Search is too long."}}), 422
    query = db.session.query(Book)
    if term:
        query = query.filter(or_(Book.title.ilike(f"%{term}%"), Book.isbn.ilike(f"%{term}%"), Book.authors.any(Author.name.ilike(f"%{term}%"))))
    total = query.count()
    books = query.order_by(Book.title.asc(), Book.id.asc()).offset((page - 1) * per_page).limit(per_page).all()
    def serialize_book(book):
        return {"id": str(book.id), "title": book.title, "subtitle": book.subtitle, "isbn": book.isbn,
                "authors": [a.name for a in book.authors], "description": book.description,
                "publication_year": book.publication_year, "publisher": book.publisher.name if book.publisher else None,
                "category": book.category.name if book.category else None,
                "copies": [{"id": str(c.id), "accession_number": c.accession_number, "barcode": c.barcode,
                            "rack": c.rack, "shelf": c.shelf, "status": c.status.value} for c in book.copies]}
    return jsonify({"status": "success", "data": {"items": [serialize_book(b) for b in books], "total": total, "page": page, "per_page": per_page}}), 200


def require_librarian():
    user = authenticated_active_user()
    if not user:
        return None, (jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401)
    if user.role not in {RoleType.LIBRARIAN, RoleType.ADMIN}:
        return None, (jsonify({"status": "error", "error": {"code": "FORBIDDEN", "message": "Librarian access required."}}), 403)
    return user, None


def valid_isbn(value):
    value = str(value or "").replace("-", "").replace(" ", "").upper()
    if len(value) == 10 and (value[:9].isdigit() and (value[9].isdigit() or value[9] == "X")):
        return sum((10 - i) * (10 if char == "X" else int(char)) for i, char in enumerate(value)) % 11 == 0
    if len(value) == 13 and value.isdigit():
        return sum(int(char) * (1 if i % 2 == 0 else 3) for i, char in enumerate(value)) % 10 == 0
    return False


@app.route("/api/librarian/catalogue", methods=["POST"])
@jwt_required()
def librarian_create_book():
    user, error = require_librarian()
    if error: return error
    data = request.get_json(silent=True) or {}
    title, isbn = str(data.get("title", "")).strip(), str(data.get("isbn", "")).replace("-", "").replace(" ", "").strip()
    if not title or len(title) > 300:
        return jsonify({"status": "error", "error": {"code": "INVALID_BOOK", "message": "Title is required (maximum 300 characters)."}}), 422
    year = data.get("publication_year")
    try: year = int(year) if year not in (None, "") else None
    except (TypeError, ValueError): return jsonify({"status": "error", "error": {"code": "INVALID_YEAR", "message": "Publication year must be an integer from 1400 to 2100."}}), 422
    if year is not None and not 1400 <= year <= 2100:
        return jsonify({"status": "error", "error": {"code": "INVALID_YEAR", "message": "Publication year must be from 1400 to 2100."}}), 422
    if isbn and not valid_isbn(isbn):
        return jsonify({"status": "error", "error": {"code": "INVALID_ISBN", "message": "ISBN checksum is invalid; provide a valid ISBN-10 or ISBN-13."}}), 422
    if isbn and db.session.query(Book.id).filter(func.replace(func.replace(Book.isbn, "-", ""), " ", "") == isbn).first():
        return jsonify({"status": "error", "error": {"code": "DUPLICATE_ISBN", "message": "A book with this ISBN already exists."}}), 409
    try:
        publisher_name = str(data.get("publisher", "")).strip()
        category_name = str(data.get("category", "")).strip()
        publisher = db.session.query(Publisher).filter(func.lower(Publisher.name) == publisher_name.lower()).first() if publisher_name else None
        category = db.session.query(Category).filter(func.lower(Category.name) == category_name.lower()).first() if category_name else None
        book = Book(title=title, isbn=isbn or None, subtitle=(str(data.get("subtitle", "")).strip() or None),
                    description=(str(data.get("description", "")).strip() or None),
                    publication_year=year, language=(str(data.get("language", "English")).strip() or "English"),
                    publisher=publisher or (Publisher(name=publisher_name) if publisher_name else None),
                    category=category or (Category(name=category_name) if category_name else None))
        db.session.add(book); db.session.flush()
        for name in data.get("authors", []):
            name = str(name).strip()
            if name:
                author = db.session.query(Author).filter(func.lower(Author.name) == name.lower()).first() or Author(name=name)
                book.authors.append(author)
        db.session.commit()
        return jsonify({"status": "success", "data": {"id": str(book.id), "title": book.title}}), 201
    except Exception:
        app.logger.exception("Catalogue book creation failed")
        db.session.rollback()
        return jsonify({"status": "error", "error": {"code": "CREATE_BOOK_FAILED", "message": "Unable to create catalogue record."}}), 500


@app.route("/api/librarian/catalogue/<book_id>", methods=["PATCH"])
@jwt_required()
def librarian_update_book(book_id):
    user, error = require_librarian()
    if error: return error
    book = db.session.get(Book, book_id)
    if not book: return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Book not found."}}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data:
        title = str(data["title"]).strip()
        if not title: return jsonify({"status": "error", "error": {"code": "INVALID_BOOK", "message": "Title cannot be empty."}}), 422
        book.title = title
    for field in ("subtitle", "description", "publication_year", "language"):
        if field in data: setattr(book, field, data[field])
    if "publication_year" in data:
        try: year = int(data["publication_year"]) if data["publication_year"] not in (None, "") else None
        except (TypeError, ValueError): return jsonify({"status": "error", "error": {"code": "INVALID_YEAR", "message": "Publication year must be an integer from 1400 to 2100."}}), 422
        if year is not None and not 1400 <= year <= 2100: return jsonify({"status": "error", "error": {"code": "INVALID_YEAR", "message": "Publication year must be from 1400 to 2100."}}), 422
        book.publication_year = year
    for field, model, relation in (("publisher", Publisher, "publisher"), ("category", Category, "category")):
        if field in data:
            value = str(data[field] or "").strip()
            entry = db.session.query(model).filter(func.lower(model.name) == value.lower()).first() if value else None
            if value and not entry: entry = model(name=value)
            setattr(book, relation, entry)
    if "isbn" in data:
        isbn = str(data["isbn"]).replace("-", "").replace(" ", "").strip()
        if isbn and not valid_isbn(isbn): return jsonify({"status": "error", "error": {"code": "INVALID_ISBN", "message": "ISBN checksum is invalid; provide a valid ISBN-10 or ISBN-13."}}), 422
        duplicate = db.session.query(Book.id).filter(Book.isbn == (isbn or None), Book.id != book.id).first() if isbn else None
        if duplicate: return jsonify({"status": "error", "error": {"code": "DUPLICATE_ISBN", "message": "A book with this ISBN already exists."}}), 409
        book.isbn = isbn or None
    if "authors" in data:
        book.authors.clear()
        for name in data["authors"]:
            name = str(name).strip()
            if name: book.authors.append(db.session.query(Author).filter(func.lower(Author.name) == name.lower()).first() or Author(name=name))
    db.session.commit()
    return jsonify({"status": "success", "data": {"id": str(book.id), "title": book.title}}), 200


@app.route("/api/librarian/catalogue/<book_id>/copies", methods=["POST"])
@jwt_required()
def librarian_add_copy(book_id):
    user, error = require_librarian()
    if error: return error
    book = db.session.get(Book, book_id)
    if not book: return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Book not found."}}), 404
    data = request.get_json(silent=True) or {}
    accession, barcode, rack, shelf = [str(data.get(k, "")).strip() for k in ("accession_number", "barcode", "rack", "shelf")]
    if not all((accession, barcode, rack, shelf)):
        return jsonify({"status": "error", "error": {"code": "INVALID_COPY", "message": "Accession number, barcode, rack and shelf are required."}}), 422
    if db.session.query(BookCopy.id).filter(or_(BookCopy.accession_number == accession, BookCopy.barcode == barcode)).first():
        return jsonify({"status": "error", "error": {"code": "DUPLICATE_COPY_ID", "message": "Accession number or barcode already exists."}}), 409
    copy = BookCopy(book_id=book.id, accession_number=accession, barcode=barcode, rack=rack, shelf=shelf, acquired_at=datetime.utcnow().date())
    db.session.add(copy); db.session.commit()
    return jsonify({"status": "success", "data": {"id": str(copy.id), "status": copy.status.value}}), 201


@app.route("/api/librarian/loans", methods=["GET"])
@jwt_required()
def librarian_loans():
    user, error = require_librarian()
    if error: return error
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip().upper()
    query = db.session.query(Loan).join(User, Loan.user_id == User.id).join(BookCopy).join(Book)
    if status == "OVERDUE": query = query.filter(or_(Loan.status == LoanStatus.OVERDUE, (Loan.status == LoanStatus.BORROWED) & (Loan.due_at < datetime.utcnow())))
    elif status == "ACTIVE": query = query.filter(Loan.status.in_((LoanStatus.BORROWED, LoanStatus.OVERDUE)))
    elif status:
        if status not in {item.value for item in LoanStatus}:
            return jsonify({"status": "error", "error": {"code": "INVALID_STATUS", "message": "Unknown loan status."}}), 422
        query = query.filter(Loan.status == LoanStatus(status))
    if q: query = query.filter(or_(User.name.ilike(f"%{q}%"), User.enrollment_id.ilike(f"%{q}%"), User.employee_id.ilike(f"%{q}%"), Book.title.ilike(f"%{q}%")))
    loans = query.order_by(Loan.due_at.asc()).limit(500).all()
    return jsonify({"status": "success", "data": [{"id": str(l.id), "book_title": l.book_copy.book.title, "borrower": l.user.name,
        "user_id": l.user.enrollment_id if l.user.role == RoleType.STUDENT else l.user.employee_id, "issued_at": l.issued_at.isoformat(),
        "due_at": l.due_at.isoformat(), "status": "OVERDUE" if l.status == LoanStatus.BORROWED and l.due_at < datetime.utcnow() else l.status.value,
        "copy_id": str(l.book_copy.id), "accession_number": l.book_copy.accession_number} for l in loans]}), 200


@app.route("/api/librarian/loans/<loan_id>/return", methods=["POST"])
@jwt_required()
def librarian_return_loan(loan_id):
    librarian, error = require_librarian()
    if error: return error
    loan = db.session.get(Loan, loan_id)
    if not loan: return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Loan not found."}}), 404
    if loan.status not in {LoanStatus.BORROWED, LoanStatus.OVERDUE}:
        return jsonify({"status": "error", "error": {"code": "INVALID_STATE", "message": "Only an active issued loan can be returned."}}), 409
    try:
        now = datetime.utcnow()
        late = loan.due_at < now
        loan.status = LoanStatus.RETURNED
        loan.returned_at = now
        loan.returned_to = librarian.id
        loan.book_copy.status = CopyStatus.AVAILABLE
        db.session.add(Notification(user_id=loan.user_id, type=NotificationType.SYSTEM, title="Book returned", message=f"{loan.book_copy.book.title} was returned successfully."))
        db.session.commit()
        return jsonify({"status": "success", "data": {"id": str(loan.id), "status": loan.status.value, "overdue_at_return": late, "returned_at": loan.returned_at.isoformat()}}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "error": {"code": "RETURN_FAILED", "message": "Unable to record book return."}}), 500


@app.route("/api/librarian/suggestions", methods=["GET"])
@jwt_required()
def librarian_suggestions():
    user, error = require_librarian()
    if error: return error
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip().upper()
    query = db.session.query(Suggestion)
    if q: query = query.filter(Suggestion.title.ilike(f"%{q}%"))
    if status:
        if status not in {x.value for x in SuggestionStatus}: return jsonify({"status": "error", "error": {"code": "INVALID_STATUS", "message": "Unknown suggestion status."}}), 422
        query = query.filter(Suggestion.status == SuggestionStatus(status))
    rows = query.order_by(Suggestion.created_at.desc()).limit(500).all()
    return jsonify({"status": "success", "data": {"items": [{"id": str(s.id), "title": s.title, "author": s.author, "status": s.status.value,
        "submitted_at": s.created_at.isoformat(), "requester": s.submitted_by_user.name, "requester_role": s.submitted_by_user.role.value,
        "votes": db.session.query(func.count(SuggestionVote.user_id)).filter_by(suggestion_id=s.id).scalar() or 0} for s in rows]}}), 200


@app.route("/api/librarian/suggestions/<suggestion_id>/review", methods=["POST"])
@jwt_required()
def librarian_review_suggestion(suggestion_id):
    librarian, error = require_librarian()
    if error: return error
    suggestion = db.session.get(Suggestion, suggestion_id)
    if not suggestion: return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Suggestion not found."}}), 404
    data = request.get_json(silent=True) or {}
    try: status = SuggestionStatus(str(data.get("status", "")).strip().upper())
    except ValueError: return jsonify({"status": "error", "error": {"code": "INVALID_STATUS", "message": "Choose a valid suggestion status."}}), 422
    if status not in {SuggestionStatus.UNDER_REVIEW, SuggestionStatus.APPROVED, SuggestionStatus.REJECTED, SuggestionStatus.ORDERED, SuggestionStatus.AVAILABLE}:
        return jsonify({"status": "error", "error": {"code": "INVALID_STATUS", "message": "This review status is not permitted."}}), 422
    suggestion.status, suggestion.reviewed_by, suggestion.reviewed_at = status, librarian.id, datetime.utcnow()
    db.session.add(Notification(user_id=suggestion.submitted_by, type=NotificationType.SUGGESTION_STATUS_CHANGED, title="Suggestion updated", message=f"Your suggestion '{suggestion.title}' is now {status.value.replace('_', ' ').lower()}."))
    db.session.commit()
    return jsonify({"status": "success", "data": {"id": str(suggestion.id), "status": status.value, "reviewed_at": suggestion.reviewed_at.isoformat()}}), 200


@app.route("/api/users/me/notifications", methods=["GET"])
@jwt_required()
def my_notifications():
    user = authenticated_active_user()
    if not user: return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    rows = db.session.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify({"status": "success", "data": {"unread": sum(not n.is_read for n in rows), "items": [{"id": str(n.id), "type": n.type.value, "title": n.title, "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in rows]}}), 200


@app.route("/api/users/me/notifications/<notification_id>/read", methods=["POST"])
@jwt_required()
def mark_notification_read(notification_id):
    user = authenticated_active_user()
    if not user: return jsonify({"status": "error", "error": {"code": "ACCOUNT_DISABLED", "message": "Active account required."}}), 401
    notification = db.session.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not notification: return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Notification not found."}}), 404
    notification.is_read = True
    db.session.commit()
    return jsonify({"status": "success", "data": {"id": str(notification.id), "is_read": True}}), 200


@app.route("/api/categories", methods=["GET"])
@jwt_required()
def list_categories():
    try:
        categories = db.session.query(Category).order_by(Category.name).all()
        return jsonify({
            "status": "success",
            "data": [{"id": str(c.id), "name": c.name} for c in categories]
        }), 200
    except Exception as e:
        app.logger.exception("Categories failed")
        return jsonify({"status": "error", "error": {"code": "CATEGORIES_FAILED", "message": str(e)}}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(
        host=app.config.get("BACKEND_HOST", "127.0.0.1"),
        port=app.config.get("BACKEND_PORT", 5001),
        debug=False,
    )