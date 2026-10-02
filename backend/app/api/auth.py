from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.core.database import get_conn
from app.core.security import create_access_token

router=APIRouter(prefix='/api/auth',tags=['auth'])
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post('/login')
def login(payload: LoginRequest):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,email,role::text AS role,department_id FROM users WHERE email=%s AND is_active=true AND password_hash=crypt(%s,password_hash)""",(payload.email,payload.password))
            user=cur.fetchone()
    if not user: raise HTTPException(401,'Invalid credentials')
    return {'access_token':create_access_token(user),'token_type':'bearer','user':user}
