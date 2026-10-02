from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.reports import router as reports_router
from app.api.meta import router as meta_router

app=FastAPI(title='MITRC LibSphere API',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(auth_router); app.include_router(reports_router); app.include_router(meta_router)
@app.get('/health')
def health(): return {'status':'ok','service':'mitrc-libsphere-api'}
