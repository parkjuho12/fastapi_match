# 매칭 앱 백엔드 API

FastAPI와 MariaDB를 사용한 매칭 앱의 백엔드 API입니다.

## 설치 및 실행

### 1. 의존성 설치
```bash
pip3 install -r requirements.txt
```

### 2. 환경변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=matching_app

# JWT 설정
SECRET_KEY=your_secret_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. MariaDB 데이터베이스 생성
MariaDB에 접속하여 데이터베이스를 생성하세요:

```sql
CREATE DATABASE matching_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 서버 실행
```bash
python main.py
```

또는

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API 엔드포인트

### 인증 관련

#### 회원가입
- **POST** `/auth/register`
- **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "홍길동",
  "birth_date": "1990-01-01",
  "gender": "M",
  "nationality": "대한민국",
  "terms_agreed": true
}
```

#### 로그인
- **POST** `/auth/login`
- **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
- **Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 내 정보 조회
- **GET** `/auth/me`
- **Headers**: `Authorization: Bearer {access_token}`

### 사용자 관련

#### 사용자 정보 조회
- **GET** `/users/{user_id}`
- **Headers**: `Authorization: Bearer {access_token}`

## 데이터베이스 스키마

### users 테이블
```sql
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash CHAR(64) NOT NULL,     -- SHA-256 해시 (HEX 64자)
  salt CHAR(32) NOT NULL,              -- Salt (16바이트를 HEX로 표현)
  name VARCHAR(100) NOT NULL,
  birth_date DATE NOT NULL,
  gender ENUM('M', 'F') NOT NULL,
  nationality VARCHAR(100) NOT NULL,
  terms_agreed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 보안 기능

1. **비밀번호 해싱**: SHA-256 + Salt를 사용한 안전한 비밀번호 저장
2. **JWT 토큰**: 인증을 위한 JWT 액세스 토큰 사용
3. **비밀번호 검증**: 최소 8자, 영문/숫자/특수문자 중 2가지 이상 포함
4. **CORS 설정**: 크로스 오리진 요청 지원

## 새로 추가된 기능들 🚀

### 고급 채팅 시스템
1대1 채팅이 대폭 업그레이드되었습니다!

#### 📁 파일 및 이미지 전송
- 이미지, 문서, 음성, 동영상 파일 업로드 지원
- 파일 타입별 크기 제한 및 검증
- 사용자별/채팅방별 분리된 저장 구조

#### 😊 메시지 반응 (이모지)
- 메시지에 이모지 반응 추가/제거
- 실시간 반응 알림
- 반응 목록 조회

#### 💬 메시지 답장/인용
- 특정 메시지에 답장 기능
- 원본 메시지 미리보기
- 답장 체인 지원

#### 🔍 메시지 검색
- 채팅방 내 메시지 내용 검색
- 페이지네이션 지원
- 빠른 검색 성능

#### ⚙️ 채팅방 개인 설정
- 알림 on/off, 알림음 선택
- 배경 테마, 글꼴 크기 설정
- 파일 자동 다운로드 설정

#### 🟢 온라인 상태 및 읽음 표시
- 실시간 온라인/오프라인 상태
- 마지막 접속 시간 표시
- 메시지 읽음 상태 추적

#### ⏰ 예약 메시지
- 미래 시간 지정하여 메시지 예약
- 자동 전송 기능

### 상세 API 가이드
- 📖 **[고급 채팅 API 가이드](고급_채팅_API_가이드.md)**: 모든 새 기능의 사용법
- 📖 **[시간표 API 가이드](시간표_API_가이드.md)**: 시간표 관리 기능
- 📖 **[알람 API 가이드](알람_API_가이드.md)**: 알림 시스템

### 테스트 스크립트
```bash
# 고급 채팅 기능 테스트
python test_advanced_chat.py
```

## 기술 스택

- **Backend**: FastAPI, Python 3.8+
- **Database**: MariaDB/MySQL
- **Authentication**: JWT
- **Real-time**: WebSocket
- **File Storage**: Local File System
- **Image Processing**: Pillow (PIL)

## 주의사항

1. 프로덕션 환경에서는 반드시 `SECRET_KEY`를 안전한 값으로 변경하세요.
2. CORS 설정에서 `allow_origins=["*"]`를 특정 도메인으로 제한하세요.
3. 데이터베이스 연결 정보를 안전하게 관리하세요.
4. HTTPS를 사용하여 통신을 암호화하세요.
5. 파일 업로드 용량 제한을 적절히 설정하세요.
6. 정적 파일 서빙을 위한 웹 서버 설정을 확인하세요.