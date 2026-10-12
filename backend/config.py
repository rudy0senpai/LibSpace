import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = False
    BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "5001"))
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")