from datetime import date
from typing import Any
from pydantic import BaseModel

class DashboardResponse(BaseModel):
    scope: dict[str, Any]
    summary: dict[str, Any]
    comparisons: dict[str, Any]
    borrowing_trend: list[dict[str, Any]]
    borrowing_by_category: list[dict[str, Any]]
    student_vs_faculty: list[dict[str, Any]]
    book_utilization: list[dict[str, Any]]
    copy_status: list[dict[str, Any]]
    suggestion_demand: list[dict[str, Any]]
    overdue_trend: list[dict[str, Any]]
    top_books: list[dict[str, Any]]
    student_vs_faculty_suggestions: list[dict[str, Any]]
    suggestion_status_distribution: list[dict[str, Any]]
    suggestions: list[dict[str, Any]]
    recent_suggestions: list[dict[str, Any]]
