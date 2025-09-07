# 🚀 배포 가이드

## 📋 배포시 환경변수 설정

배포 환경에서는 보안을 위해 다음 환경변수들을 설정해주세요:

### 🗄️ 데이터베이스 설정
```bash
export DB_HOST=your_database_host
export DB_PORT=3306
export DB_USER=your_database_user
export DB_PASSWORD=your_database_password
export DB_NAME=your_database_name
```

### 🔐 JWT 설정
```bash
export SECRET_KEY=your-very-strong-secret-key-minimum-32-characters
export ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 📧 이메일 설정
```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=465
export SMTP_USER=your_email@gmail.com
export SMTP_PASSWORD=your_gmail_app_password
export EMAIL_TEST_MODE=false
```

## 🔧 .env 파일 방식 (권장)

1. 프로젝트 루트에 `.env` 파일 생성:
```env
# 데이터베이스 설정
DB_HOST=your_database_host
DB_PORT=3306
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=your_database_name

# JWT 설정
SECRET_KEY=your-very-strong-secret-key-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 이메일 설정
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
EMAIL_TEST_MODE=false
```

2. `.env` 파일이 Git에 업로드되지 않는지 확인 (`.gitignore`에 포함됨)

## ⚠️ 보안 주의사항

1. **SECRET_KEY**: 최소 32자 이상의 강력한 랜덤 문자열 사용
2. **DB_PASSWORD**: 강력한 데이터베이스 비밀번호 설정
3. **SMTP_PASSWORD**: Gmail 앱 비밀번호 사용 (일반 비밀번호 X)
4. **환경변수 파일**: `.env` 파일은 절대 Git에 업로드하지 마세요

## 🧪 개발 vs 배포

- **개발**: 기본값 사용 (현재 설정)
- **배포**: 환경변수 필수 설정

개발 단계에서는 별도 설정 없이 바로 사용 가능하며, 배포시에만 환경변수를 설정하면 됩니다.