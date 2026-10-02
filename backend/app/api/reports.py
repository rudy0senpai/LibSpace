from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from app.core.security import get_current_user
from app.services.report_service import ReportService

router=APIRouter(prefix='/api/reports',tags=['reports'])
service=ReportService()

@router.get('/department/dashboard')
def department_dashboard(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    category_id: str | None = Query(None),
    user_type: str | None = Query(None),
    suggestion_status: str | None = Query(None),
    search: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get('role') not in ('DEPARTMENT','ADMIN','LIBRARIAN'):
        raise HTTPException(403,'REPORT_VIEW permission required')
    if current_user.get('role') == 'DEPARTMENT':
        department_id=current_user.get('department_id')
    else:
        department_id=current_user.get('department_id')
        if not department_id:
            department_id='00000000-0000-0000-0000-000000000001'
    end=end_date or date.today()+timedelta(days=1)
    start=start_date or (end-timedelta(days=183))
    return service.dashboard(department_id,start,end,category_id,user_type,suggestion_status,search)
