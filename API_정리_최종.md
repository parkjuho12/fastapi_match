# 🚀 매칭 앱 API 최종 정리

## 📋 **구현 완료된 API 목록**

---

## 🔐 **인증 시스템**

### 1. **회원가입 & 로그인**
- `POST /auth/request-email-verification` - 이메일 인증번호 발송
- `POST /auth/verify-email` - 이메일 인증번호 확인
- `POST /auth/register` - 회원가입
- `POST /auth/login` - 로그인
- `POST /auth/logout` - 로그아웃

### 2. **사용자 정보 관리**
- `GET /auth/me` - **현재 사용자 정보 조회 (확장됨)**
  - 기본 정보 (이름, 이메일, 생년월일, 성별 등)
  - **학과, 재학상태**
  - **온보딩 정보 (친구유형, 흡연/음주, MBTI)**
  - **성격/관심사 키워드**
  - **온보딩 완료 여부**

### 3. **아이디/비밀번호 찾기**
- `POST /auth/find-user-id` - 아이디 찾기
- `POST /auth/request-password-reset` - 비밀번호 재설정 요청
- `POST /auth/verify-password-reset` - 비밀번호 재설정 인증
- `POST /auth/reset-password` - 새 비밀번호 설정

---

## 👤 **사용자 프로필 관리**

### 1. **개인정보 수정**
- `PUT /api/users/profile` - **이름 수정**
- `PUT /api/users/onboarding/profile` - **온보딩 정보 수정**
  - 학과, 재학상태, 친구유형, 흡연/음주, MBTI, 키워드 등

### 2. **프로필 조회**
- `GET /api/users/{user_id}/profile` - 특정 사용자 프로필 조회
- `GET /api/users/{user_id}/onboarding/progress` - 온보딩 진행상황 조회

### 3. **온보딩 완료**
- `POST /api/users/{user_id}/onboarding/complete` - 온보딩 완료 처리

---

## 📅 **시간표 시스템**

### 1. **시간표 관리**
- `POST /timetables/` - 시간표 생성
- `GET /timetables/` - 사용자 시간표 목록 조회
- `GET /timetables/active` - 활성 시간표 조회 (주간 형태)
- `PUT /timetables/{timetable_id}` - 시간표 수정
- `DELETE /timetables/{timetable_id}` - 시간표 삭제

### 2. **과목 관리**
- `POST /timetables/{timetable_id}/subjects` - 과목 추가
- `PUT /timetables/{timetable_id}/subjects/{subject_id}` - 과목 수정
- `DELETE /timetables/{timetable_id}/subjects/{subject_id}` - 과목 제거

---

## 💬 **채팅 시스템**

### 1. **채팅방 관리**
- `POST /chat/rooms/` - 채팅방 생성
- `GET /chat/rooms/` - 참여 중인 채팅방 목록 조회
- `GET /chat/rooms/{room_id}/messages/` - 채팅방 메시지 조회

### 2. **실시간 채팅**
- `WebSocket /ws/chat/{room_id}` - 실시간 채팅 연결
- 메시지 전송/수신, 답장, 파일 전송, 반응(이모지) 지원

### 3. **고급 채팅 기능**
- `POST /chat/upload/` - 파일 업로드 (이미지, 문서, 음성, 동영상)
- `POST /chat/messages/{message_id}/reactions/` - 메시지 반응 추가
- `DELETE /chat/messages/{message_id}/reactions/{emoji}` - 메시지 반응 제거
- `GET /chat/messages/{message_id}/reactions/` - 메시지 반응 조회
- `GET /chat/rooms/{room_id}/search/` - 채팅방 내 메시지 검색

---

## 🔔 **알람 시스템**

### 1. **알람 조회**
- `GET /notifications/` - 알람 목록 조회 (페이지네이션)
- `GET /notifications/stats` - 알람 통계 조회

### 2. **알람 관리**
- `POST /notifications/mark-read` - 선택한 알람 읽음 처리
- `POST /notifications/mark-all-read` - 모든 알람 읽음 처리
- `DELETE /notifications/{notification_id}` - 알람 삭제

### 3. **알람 타입**
- **chat**: 채팅 메시지 관련 알람
- **timetable**: 시간표/수업 관련 알람
- **match**: 매칭 관련 알람
- **system**: 시스템 공지사항
- **reminder**: 사용자 설정 리마인더

---

## 📊 **데이터베이스 구조**

### **Users 테이블** (기본 회원가입 정보)
- `user_id`, `email`, `password_hash`, `salt`
- `name`, `birth_date`, `gender`, `nationality`
- `phone_number`, `terms_agreed`, `created_at`

### **UserProfiles 테이블** (온보딩 정보)
- `profile_id`, `user_id`
- `department` (학과), `student_status` (재학상태)
- `friend_type`, `smoking`, `drinking`, `mbti`
- `onboarding_completed`, `onboarding_completed_at`

### **UserKeywords 테이블** (키워드 정보)
- `keyword_id`, `user_id`
- `keyword_type` (personality, interest, friend_style)
- `keyword_name`

---

## 🔧 **주요 변경사항**

### 1. **사용자 정보 구조 개선**
- ✅ User 테이블에서 중복 컬럼 제거 (department, student_status)
- ✅ 모든 온보딩 정보는 UserProfile에서 관리
- ✅ GET /auth/me API 확장으로 모든 정보를 한 번에 제공

### 2. **새로운 API 추가**
- ✅ `PUT /api/users/profile` - 이름 수정
- ✅ `PUT /api/users/onboarding/profile` - 온보딩 정보 수정

### 3. **데이터 일관성 향상**
- ✅ 중복 데이터 제거로 데이터 무결성 확보
- ✅ 논리적 구조로 API 사용성 개선

---

## 📱 **프론트엔드 연동 예시**

### **사용자 정보 조회**
```javascript
// GET /auth/me 호출 시 받는 정보
{
  "user_id": 10,
  "name": "박주호",
  "email": "pjhjh2350@kbu.ac.kr",
  "department": "컴퓨터공학과",        // UserProfile에서
  "student_status": "재학",           // UserProfile에서
  "friend_type": "학습형",            // UserProfile에서
  "smoking": "비흡연",                // UserProfile에서
  "drinking": "가끔",                 // UserProfile에서
  "mbti": "INTJ",                    // UserProfile에서
  "personality_keywords": ["창의적인", "논리적인", "차분한"],
  "interest_keywords": ["프로그래밍", "게임", "영화"],
  "onboarding_completed": true
}
```

### **개인정보 수정**
```javascript
// PUT /api/users/profile - 이름 수정
{
  "name": "새로운 이름"
}

// PUT /api/users/onboarding/profile - 온보딩 정보 수정
{
  "department": "소프트웨어공학과",
  "student_status": "재학",
  "mbti": "ENFP"
}
```

---

## 🎯 **API 사용 시 주의사항**

1. **인증 필수**: 모든 API는 Bearer 토큰 인증 필요
2. **사용자 격리**: 각 사용자는 본인의 정보만 조회/수정 가능
3. **온보딩 완료**: 온보딩 관련 API는 온보딩 완료 후 사용 가능
4. **데이터 검증**: 모든 입력 데이터는 서버에서 검증됨

---

## 📚 **상세 가이드 문서**

- 📖 [알람_API_가이드.md](./알람_API_가이드.md) - 알람 시스템 상세 가이드
- 📖 [채팅_API_가이드.md](./채팅_API_가이드.md) - 채팅 시스템 상세 가이드
- 📖 [시간표_API_가이드.md](./시간표_API_가이드.md) - 시간표 시스템 상세 가이드

---

**모든 API가 구현 완료되었습니다! 🎉**

프론트엔드에서 이 API들을 활용하여 완전한 매칭 앱을 구현할 수 있습니다.
