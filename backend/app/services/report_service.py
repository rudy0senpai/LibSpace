from datetime import date, timedelta
from fastapi import HTTPException
from app.repositories.report_repository import ReportRepository

class ReportService:
    def __init__(self): self.repo=ReportRepository()

    @staticmethod
    def pct(current, previous):
        if previous in (0,None): return None
        return round((current-previous)/previous*100,1)

    def dashboard(self, department_id, start, end, category_id=None,user_type=None,suggestion_status=None,search=None):
        if start >= end: raise HTTPException(422,'start_date must be before end_date')
        scope=self.repo.scope(department_id)
        if not scope: raise HTTPException(404,'Department not found')
        current=self.repo.summary(department_id,start,end); previous=self.repo.previous_summary(department_id,start,end)
        def n(k,row): return int(row[k] or 0)
        comparisons={f'{k}_change':self.pct(n(k,current),n(k,previous)) for k in current.keys()}
        return {
            'scope': {**scope,'start_date':start,'end_date':end},
            'summary': {k:n(k,current) for k in current.keys()},
            'comparisons': comparisons,
            'borrowing_trend': self.repo.borrowing_trend(department_id,start,end),
            'borrowing_by_category': self.repo.borrowing_by_category(department_id,start,end,category_id,user_type),
            'student_vs_faculty': self.repo.student_vs_faculty(department_id,start,end),
            'book_utilization': self.repo.utilization(department_id,start,end),
            'copy_status': self.repo.copy_status(department_id),
            'suggestion_demand': self.repo.suggestion_demand(department_id,start,end,category_id,suggestion_status),
            'overdue_trend': self.repo.overdue_trend(department_id,start,end),
            'top_books': self.repo.top_books(department_id),
            'student_vs_faculty_suggestions': self.repo.student_faculty_suggestions(department_id,start,end),
            'suggestion_status_distribution': self.repo.suggestion_status(department_id),
            'suggestions': self.repo.suggestions(department_id,start,end,search,suggestion_status,category_id,user_type),
            'recent_suggestions': self.repo.suggestions(department_id,start,end,limit=5),
        }
