import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pathlib import Path
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy.engine import URL
from sqlalchemy import func, text, case, inspect, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash
from werkzeug.exceptions import HTTPException

from config import Config
from models import db, User, RoleType, Department, Book, BookCopy, Loan, Suggestion, SuggestionVote, Category, CopyStatus, LoanStatus, SuggestionStatus, SuggestionReason, Author

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
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    category_id = request.args.get("category_id")
    user_type = request.args.get("user_type")
    suggestion_status = request.args.get("suggestion_status")
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

        if start_date and end_date and start_date >= end_date:
            raise ValueError()

    except ValueError:
        raise ValueError("Invalid dates")

    if user_type and user_type not in USER_TYPES:
        raise ValueError("Invalid user type")

    if suggestion_status and suggestion_status not in SUGGESTION_STATUSES:
        raise ValueError("Invalid suggestion status")

    if category_id is not None and (not category_id or len(category_id) > 100):
        raise ValueError("Invalid category ID")

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


def get_department_dashboard_data(department_id, filters):
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    category_id = filters.get("category_id")
    user_type = filters.get("user_type")
    suggestion_status = filters.get("suggestion_status")
    search = filters.get("search")

    if not start_date:
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

    dept = db.session.get(Department, department_id)
    if not dept:
        return None

    kpis = {}
    comparisons = {}
    charts = {}
    rankings = {}
    suggestions_data = {}

    dept_books_count = db.session.query(func.count(func.distinct(Book.id))).join(
        Book.departments
    ).filter(Department.id == department_id).scalar()
    kpis["department_books"] = dept_books_count or 0

    copy_statuses = db.session.query(BookCopy.status, func.count(BookCopy.id)).join(
        Book, BookCopy.book_id == Book.id
    ).join(Book.departments).filter(Department.id == department_id).group_by(BookCopy.status).all()

    status_map = {status.value: count for status, count in copy_statuses}
    kpis["available_copies"] = status_map.get("AVAILABLE", 0)
    kpis["currently_borrowed"] = status_map.get("BORROWED", 0)
    kpis["overdue_books"] = 0

    overdue_count = db.session.query(func.count(Loan.id)).join(
        BookCopy, Loan.book_copy_id == BookCopy.id
    ).join(Book, BookCopy.book_id == Book.id
    ).join(Book.departments).filter(
        Department.id == department_id,
        Loan.status == LoanStatus.OVERDUE
    ).scalar()
    kpis["overdue_books"] = overdue_count or 0

    active_students = db.session.query(func.count(func.distinct(User.id))).filter(
        User.department_id == department_id,
        User.role == RoleType.STUDENT,
        User.is_active == True
    ).scalar()
    kpis["active_students"] = active_students or 0

    active_faculty = db.session.query(func.count(func.distinct(User.id))).filter(
        User.department_id == department_id,
        User.role == RoleType.FACULTY,
        User.is_active == True
    ).scalar()
    kpis["active_faculty"] = active_faculty or 0

    pending_suggestions = db.session.query(func.count(Suggestion.id)).join(
        User, Suggestion.submitted_by == User.id
    ).filter(
        User.department_id == department_id,
        Suggestion.status == SuggestionStatus.UNDER_REVIEW
    ).scalar()
    kpis["pending_suggestions"] = pending_suggestions or 0

    total_votes = db.session.query(func.count(SuggestionVote.suggestion_id)).join(
        Suggestion, SuggestionVote.suggestion_id == Suggestion.id
    ).join(User, Suggestion.submitted_by == User.id).filter(
        User.department_id == department_id
    ).scalar()
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
    ).filter(
        Department.id == department_id,
        Loan.issued_at >= start_dt,
        Loan.issued_at < end_dt
    ).group_by('month').order_by('month').all()

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
    ).filter(
        Department.id == department_id,
        Loan.issued_at >= start_dt,
        Loan.issued_at < end_dt
    ).group_by(Category.name).order_by(func.count(Loan.id).desc()).all()

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
    ).filter(
        Department.id == department_id,
        Loan.issued_at >= start_dt,
        Loan.issued_at < end_dt
    ).group_by('month').order_by('month').all()

    charts["student_vs_faculty_borrowing"] = [
        {"period": month_label(row.month), "students": row.students, "faculty": row.faculty} for row in student_vs_faculty
    ]

    utilization = db.session.query(
        month_bucket(Loan.issued_at).label('month'),
        (func.count(Loan.id) * 100.0 / func.nullif(kpis["department_books"], 0)).label('utilization_rate')
    ).join(BookCopy, Loan.book_copy_id == BookCopy.id).join(
        Book, BookCopy.book_id == Book.id
    ).join(Book.departments).filter(
        Department.id == department_id,
        Loan.issued_at >= start_dt,
        Loan.issued_at < end_dt
    ).group_by('month').order_by('month').all()

    charts["department_book_utilization"] = [
        {"period": month_label(row.month), "utilization_rate": round(float(row.utilization_rate or 0), 1)} for row in utilization
    ]

    charts["book_copy_status"] = [
        {"status": status.value if hasattr(status, 'value') else str(status), "count": count} for status, count in copy_statuses
    ]

    suggestion_demand = db.session.query(
        Category.name.label('category_name'),
        func.count(Suggestion.id).label('suggestion_count')
    ).join(
        User, Suggestion.submitted_by == User.id
    ).outerjoin(
        Category, Suggestion.category_id == Category.id
    ).filter(
        User.department_id == department_id,
        Suggestion.created_at >= start_dt,
        Suggestion.created_at < end_dt
    ).group_by(Category.name).order_by(func.count(Suggestion.id).desc()).all()

    charts["suggestion_demand_by_category"] = [
        {"category_name": row.category_name or "Uncategorized", "suggestion_count": row.suggestion_count} for row in suggestion_demand
    ]

    overdue_trend = db.session.query(
        month_bucket(Loan.due_at).label('month'),
        func.count(Loan.id).label('overdue_count')
    ).join(BookCopy, Loan.book_copy_id == BookCopy.id).join(
        Book, BookCopy.book_id == Book.id
    ).join(Book.departments).filter(
        Department.id == department_id,
        Loan.status == LoanStatus.OVERDUE,
        Loan.due_at >= start_dt,
        Loan.due_at < end_dt
    ).group_by('month').order_by('month').all()

    charts["overdue_trend"] = [
        {"period": month_label(row.month), "overdue_count": row.overdue_count} for row in overdue_trend
    ]

    top_borrowed = db.session.query(
        Book.title, func.count(Loan.id).label('borrow_count')
    ).join(BookCopy, Book.id == BookCopy.book_id).join(
        Loan, BookCopy.id == Loan.book_copy_id
    ).join(Book.departments).filter(
        Department.id == department_id,
        Loan.issued_at >= start_dt,
        Loan.issued_at < end_dt
    ).group_by(Book.id, Book.title).order_by(func.count(Loan.id).desc()).limit(5).all()

    rankings["top_borrowed_books"] = [
        {"title": row.title, "author": "", "borrow_count": row.borrow_count} for row in top_borrowed
    ]

    top_suggested = db.session.query(
        Suggestion.title,
        func.count(SuggestionVote.suggestion_id).label('vote_count'),
        func.max(Suggestion.created_at).label('created_at')
    ).join(User, Suggestion.submitted_by == User.id).outerjoin(
        SuggestionVote, Suggestion.id == SuggestionVote.suggestion_id
    ).filter(
        User.department_id == department_id
    ).group_by(Suggestion.id, Suggestion.title).order_by(
        func.count(SuggestionVote.suggestion_id).desc(), Suggestion.created_at.asc(), Suggestion.title.asc()
    ).limit(5).all()

    rankings["top_suggested_books"] = [
        {"title": row.title, "vote_count": row.vote_count, "created_at": row.created_at.isoformat() if row.created_at else None} for row in top_suggested
    ]

    student_suggestions = db.session.query(func.count(Suggestion.id)).join(
        User, Suggestion.submitted_by == User.id
    ).filter(
        User.department_id == department_id,
        User.role == RoleType.STUDENT
    ).scalar()
    faculty_suggestions = db.session.query(func.count(Suggestion.id)).join(
        User, Suggestion.submitted_by == User.id
    ).filter(
        User.department_id == department_id,
        User.role == RoleType.FACULTY
    ).scalar()

    suggestions_data["student_vs_faculty"] = {
        "student": student_suggestions or 0,
        "faculty": faculty_suggestions or 0
    }

    status_dist = db.session.query(Suggestion.status, func.count(Suggestion.id)).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id).group_by(Suggestion.status).all()

    suggestions_data["status_distribution"] = {status.value: count for status, count in status_dist}

    suggestions_query = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id)

    if suggestion_status:
        suggestions_query = suggestions_query.filter(Suggestion.status == SuggestionStatus(suggestion_status))

    if search:
        suggestions_query = suggestions_query.filter(
            (Suggestion.title.ilike(f"%{search}%")) |
            (Suggestion.author.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )

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

    recent_suggestions = db.session.query(Suggestion).join(
        User, Suggestion.submitted_by == User.id
    ).filter(User.department_id == department_id).order_by(
        Suggestion.created_at.desc()
    ).limit(5).all()

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

    return {
        "scope": {"id": str(dept.id), "name": dept.name},
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
        name = str(data.get("name", "")).strip()
        user_id = str(data.get("user_id", "")).strip()
        requested_role = str(data.get("role", "")).strip().upper()
        if requested_role == "TEACHER":
            requested_role = "FACULTY"
        demo_profiles = {
            ("Urvashi", "25EMCAD016", "STUDENT"),
            ("Yashdeep", "25TECAD016", "FACULTY"),
            ("Dhruv", "25DMCAD016", "DEPARTMENT"),
            ("Sphere", "25LIB016", "LIBRARIAN"),
        }
        if (name, user_id, requested_role) not in demo_profiles:
            return jsonify({"status": "error", "error": {
                "code": "INVALID_IDENTITY", "message": "Name, user ID, and role did not match a permitted local testing profile."
            }}), 401
        role = RoleType(requested_role)
        identifier_field = User.enrollment_id if role == RoleType.STUDENT else User.employee_id
        user = db.session.query(User).filter(
            User.name == name,
            identifier_field == user_id,
            User.role == role,
            User.is_active.is_(True),
        ).first()
        if not user:
            return jsonify({"status": "error", "error": {
                "code": "INVALID_IDENTITY", "message": "The local testing profile is not present in the active database."
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
        current_user_id = get_jwt_identity()
        user = db.session.get(User, current_user_id)

        if not user:
            return jsonify({"status": "error", "error": {"code": "USER_NOT_FOUND", "message": "User not found"}}), 404

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
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify({"status": "error", "error": {
            "code": "USER_NOT_FOUND", "message": "User not found"
        }}), 404
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
        query = request.args.get("q", "").strip()
        print(f"DEBUG: Search query: {query}")
        category_id = request.args.get("category_id")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        q = db.session.query(Book).join(Book.category).join(Book.departments)

        if query:
            q = q.filter(
                (Book.title.ilike(f"%{query}%")) |
                (Book.authors.any(Author.name.ilike(f"%{query}%"))) |
                (Book.isbn.ilike(f"%{query}%"))
            )
        print(f"DEBUG: Query: {q}")
        if category_id:
            q = q.filter(Book.category_id == category_id)

        total = q.count()
        books = q.offset((page - 1) * per_page).limit(per_page).all()

        results = []
        for book in books:
            copies = db.session.query(BookCopy).filter(BookCopy.book_id == book.id).all()
            avail = sum(1 for c in copies if c.status == CopyStatus.AVAILABLE)
            total_copies = len(copies)
            results.append({
                "id": str(book.id),
                "title": book.title,
                "author": ", ".join([a.name for a in book.authors]) or "",
                "isbn": book.isbn,
                "category": book.category.name if book.category else "",
                "available": avail,
                "total": total_copies,
                "rack": copies[0].rack if copies else ""
            })

        return jsonify({
            "status": "success",
            "data": {
                "items": results,
                "total": total,
                "page": page,
                "per_page": per_page
            }
        }), 200
    except Exception as e:
        app.logger.exception("Book search failed")
        return jsonify({"status": "error", "error": {"code": "SEARCH_FAILED", "message": str(e)}}), 500


@app.route("/api/users/me/loans", methods=["GET"])
@jwt_required()
def my_loans():
    try:
        current_user_id = get_jwt_identity()
        loans = db.session.query(Loan).filter(Loan.user_id == current_user_id).order_by(Loan.issued_at.desc()).all()

        results = []
        for loan in loans:
            book = loan.book_copy.book
            results.append({
                "id": str(loan.id),
                "book_title": book.title,
                "book_author": ", ".join([a.name for a in book.authors]) or "",
                "issued_at": loan.issued_at.isoformat(),
                "due_at": loan.due_at.isoformat(),
                "returned_at": loan.returned_at.isoformat() if loan.returned_at else None,
                "status": loan.status.value,
                "rack": loan.book_copy.rack,
                "shelf": loan.book_copy.shelf
            })

        return jsonify({
            "status": "success",
            "data": results
        }), 200
    except Exception as e:
        app.logger.exception("My loans failed")
        return jsonify({"status": "error", "error": {"code": "LOANS_FAILED", "message": str(e)}}), 500


@app.route("/api/users/me/suggestions", methods=["GET"])
@jwt_required()
def my_suggestions():
    try:
        current_user_id = get_jwt_identity()
        suggestions = db.session.query(Suggestion).filter(Suggestion.submitted_by == current_user_id).order_by(Suggestion.created_at.desc()).all()

        results = []
        for s in suggestions:
            vote_count = db.session.query(func.count(SuggestionVote.user_id)).filter(SuggestionVote.suggestion_id == s.id).scalar()
            results.append({
                "id": str(s.id),
                "title": s.title,
                "author": s.author or "",
                "reason": s.reason.value,
                "status": s.status.value,
                "votes": vote_count or 0,
                "created_at": s.created_at.isoformat()
            })

        return jsonify({
            "status": "success",
            "data": results
        }), 200
    except Exception as e:
        app.logger.exception("My suggestions failed")
        return jsonify({"status": "error", "error": {"code": "SUGGESTIONS_FAILED", "message": str(e)}}), 500


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
        current_user_id = get_jwt_identity()
        suggestion = db.session.get(Suggestion, suggestion_id)
        if not suggestion:
            return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Suggestion not found"}}), 404

        existing = db.session.query(SuggestionVote).filter(
            SuggestionVote.suggestion_id == suggestion_id,
            SuggestionVote.user_id == current_user_id
        ).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"status": "success", "data": {"voted": False}}), 200

        vote = SuggestionVote(suggestion_id=suggestion_id, user_id=current_user_id)
        db.session.add(vote)
        db.session.commit()

        return jsonify({"status": "success", "data": {"voted": True}}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.exception("Vote failed")
        return jsonify({"status": "error", "error": {"code": "VOTE_FAILED", "message": str(e)}}), 500


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