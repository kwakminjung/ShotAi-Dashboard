import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

TRITON_SERVER = os.getenv("TRITON_SERVER", "https://www.shotai.us/")

# NATS 설정
NATS_SERVER = os.getenv("NATS_SERVER", "wss://localhost:4222")

# FastAPI 서버 설정
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = int(os.getenv("API_PORT", 8000))

# MySQL 설정
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "shotai")

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# FastAPI 서버 URL
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# MySQL 연결 문자열
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
