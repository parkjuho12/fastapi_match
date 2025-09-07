"""
이메일 설정 모듈
환경변수에서 이메일 설정을 로드합니다.

환경변수 설정 방법:
1. .env 파일 생성
2. 아래 변수들을 설정:
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   EMAIL_TEST_MODE=false
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def get_email_settings():
    """이메일 설정을 반환합니다 (개발용 기본값, 배포시 환경변수 사용)"""
    
    # 환경변수에서 값 가져오기 (개발용 기본값 포함)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER", "pjhjh2350@gmail.com")
    smtp_password = os.getenv("SMTP_PASSWORD", "yongbhikohcamfqj")  # 개발용 앱 비밀번호
    test_mode = os.getenv("EMAIL_TEST_MODE", "false").lower() == "true"
    
    return {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "test_mode": test_mode
    }