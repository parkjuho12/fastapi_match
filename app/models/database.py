import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# MariaDB 연결 설정 (개발용 기본값, 배포시 환경변수 사용)
DB_HOST = os.getenv("DB_HOST", "pjh.pjhpjh.kr")
DB_PORT = os.getenv("DB_PORT", "1127")
DB_USER = os.getenv("DB_USER", "pjh") 
DB_PASSWORD = os.getenv("DB_PASSWORD", "qkrwngh2350@")
DB_NAME = os.getenv("DB_NAME", "SyncUp")

# 데이터베이스 URL 구성 (PyMySQL 사용)
# 비밀번호에 특수문자가 있을 경우 URL 인코딩
import urllib.parse
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 개발 시 True로 설정하면 SQL 쿼리 로그 출력
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_recycle=3600,   # 1시간마다 연결 재생성
)

# 세션 로컬 클래스
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

# 데이터베이스 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 테이블 생성
def create_tables():
    Base.metadata.create_all(bind=engine)
