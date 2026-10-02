from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.core.database import get_conn
router=APIRouter(prefix='/api/meta',tags=['meta'])
@router.get('/categories')
def categories(current_user:dict=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id,name FROM categories ORDER BY name')
            return cur.fetchall()
