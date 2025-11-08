import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# MariaDB 연결 설정 (개발용 기본값, 배포시 환경변수 사용)
DB_HOST = os.getenv("DB_HOST", "cc.pjhpjh.kr")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "pjh") 
DB_PASSWORD = os.getenv("DB_PASSWORD", "qkrwngh2350@")
DB_NAME = os.getenv("DB_NAME", "syncup")

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
    """
    FOREIGN KEY 제약조건 없이 테이블 생성
    (데이터베이스 사용자에게 REFERENCES 권한이 없는 경우)
    
    참고: ForeignKey 제약조건이 없어도 SQLAlchemy의 relationship은 정상 작동합니다.
    애플리케이션 레벨에서 참조 무결성을 관리해야 합니다.
    """
    from sqlalchemy import event, inspect
    from sqlalchemy.schema import DDL
    import re
    
    # SQL 실행 전에 FOREIGN KEY 제거하는 이벤트 리스너
    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def remove_foreign_keys(conn, cursor, statement, parameters, context, executemany):
        # statement가 문자열인 경우에만 처리
        if isinstance(statement, str):
            original = statement
            upper_stmt = statement.upper()
            
            # CREATE TABLE 문인지 확인
            if "CREATE TABLE" in upper_stmt:
                # 1. 테이블 레벨 FOREIGN KEY 제약조건 제거 (FOREIGN KEY(...) REFERENCES ... 전체)
                statement = re.sub(
                    r',\s*FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+[`"]?(\w+)[`"]?\.?[`"]?(\w+)[`"]?\s*\([^)]+\)',
                    '',
                    statement,
                    flags=re.IGNORECASE | re.MULTILINE
                )
                # 2. 컬럼 정의 내부의 REFERENCES 제거 (컬럼 타입 뒤의 REFERENCES ...)
                statement = re.sub(
                    r'\s+REFERENCES\s+[`"]?(\w+)[`"]?\.?[`"]?(\w+)[`"]?\s*\([^)]+\)',
                    '',
                    statement,
                    flags=re.IGNORECASE
                )
                # 3. FOREIGN KEY(컬럼) 만 남은 경우 제거 (REFERENCES가 이미 제거되어 FOREIGN KEY만 남은 경우)
                # 마지막에 오는 경우: , FOREIGN KEY(...) )
                statement = re.sub(
                    r',\s*FOREIGN\s+KEY\s*\([^)]+\)\s*\)',
                    ')',
                    statement,
                    flags=re.IGNORECASE
                )
                # 중간에 오는 경우: , FOREIGN KEY(...) ,
                statement = re.sub(
                    r',\s*FOREIGN\s+KEY\s*\([^)]+\)\s*,',
                    ',',
                    statement,
                    flags=re.IGNORECASE
                )
                # 줄 끝에 오는 경우
                statement = re.sub(
                    r',\s*FOREIGN\s+KEY\s*\([^)]+\)\s*$',
                    '',
                    statement,
                    flags=re.IGNORECASE | re.MULTILINE
                )
                
                if statement != original:
                    return statement, parameters
        
        return statement, parameters
    
    try:
        # 테이블 생성 시도
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✅ 데이터베이스 테이블 생성/확인 완료")
    except Exception as e:
        error_str = str(e)
        
        # 데이터베이스 연결 오류인 경우
        if "2003" in error_str or "Connection refused" in error_str or "Can't connect" in error_str:
            print("❌ 데이터베이스 연결 실패")
            print(f"   호스트: {DB_HOST}:{DB_PORT}")
            print(f"   데이터베이스: {DB_NAME}")
            print("   가능한 원인:")
            print("   1. 데이터베이스 서버가 실행 중이 아닙니다")
            print("   2. 네트워크 연결 문제 (인터넷/VPN 확인)")
            print("   3. 호스트/포트 정보가 잘못되었습니다")
            print("   4. 방화벽이 포트를 차단하고 있습니다")
            print(f"   에러 상세: {error_str[:200]}")
            # 연결 오류는 앱 시작을 막지 않도록 경고만 출력
            print("⚠️  데이터베이스 연결 실패로 앱이 시작되었지만, DB 기능은 사용할 수 없습니다.")
            return
        
        # FOREIGN KEY 권한 오류인 경우
        elif "REFERENCES" in error_str or "1142" in error_str:
            print("⚠️  FOREIGN KEY 권한 오류 발생")
            print("   이벤트 리스너로 FOREIGN KEY를 제거하려고 시도했지만 실패했습니다.")
            print("   해결 방법:")
            print("   1. 데이터베이스 관리자에게 REFERENCES 권한 요청")
            print("   2. 또는 FOREIGN KEY 없이 테이블을 수동으로 생성")
            print(f"   에러: {error_str[:300]}")
            # 에러를 다시 발생시켜서 사용자가 알 수 있도록 함
            raise Exception(f"FOREIGN KEY 권한 오류: {error_str[:200]}")
        else:
            # 다른 오류는 그대로 발생시킴
            print(f"❌ 데이터베이스 초기화 에러: {e}")
            import traceback
            traceback.print_exc()
            raise
