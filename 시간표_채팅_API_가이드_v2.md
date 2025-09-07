# 📅💬 시간표 & 채팅 API 가이드 (v2.0)

## 📋 목차
1. [시간표 API](#시간표-api)
2. [채팅 API](#채팅-api)
3. [고급 채팅 기능](#고급-채팅-기능)
4. [WebSocket 실시간 채팅](#websocket-실시간-채팅)
5. [프로필 & 이미지 관리](#프로필--이미지-관리)
6. [알람 시스템](#알람-시스템)

---

## 📅 시간표 API

### 1. 과목 관리

#### 📝 과목 생성
```http
POST /subjects/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "subject_name": "소프트웨어공학",
  "professor_name": "김교수",
  "classroom": "우당관 401호",
  "day_of_week": "월",
  "start_time": "09:00:00",
  "end_time": "10:30:00"
}
```

> ✅ **개선사항**: 요일이 이제 `String` 타입으로 자유롭게 입력 가능

**성공 응답 (201 Created):**
```json
{
  "subject_id": 1,
  "user_id": 1,
  "subject_name": "소프트웨어공학",
  "professor_name": "김교수",
  "classroom": "우당관 401호",
  "day_of_week": "월",
  "start_time": "09:00:00",
  "end_time": "10:30:00",
  "created_at": "2024-01-15T09:00:00"
}
```

#### 📋 과목 목록 조회
```http
GET /subjects/
Authorization: Bearer {access_token}
```

#### 🔍 특정 과목 조회
```http
GET /subjects/{subject_id}
Authorization: Bearer {access_token}
```

#### ✏️ 과목 수정
```http
PUT /subjects/{subject_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "subject_name": "고급소프트웨어공학",
  "classroom": "우당관 301호"
}
```

#### 🗑️ 과목 삭제
```http
DELETE /subjects/{subject_id}
Authorization: Bearer {access_token}
```

### 2. 시간표 관리

#### 📝 시간표 생성
```http
POST /timetables/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "semester": "2024-2",
  "year": 2024,
  "is_active": true
}
```

#### 🎯 활성 시간표 조회
```http
GET /timetables/active
Authorization: Bearer {access_token}
```

> ✅ **자동 생성**: 활성 시간표가 없으면 기본 시간표(2024-2)가 자동 생성됩니다.

**응답 예시:**
```json
{
  "timetable": {
    "timetable_id": 1,
    "user_id": 1,
    "semester": "2024-2",
    "year": 2024,
    "is_active": true,
    "created_at": "2024-01-15T09:00:00"
  },
  "schedule": {
    "월": [
      {
        "subject_id": 1,
        "subject_name": "소프트웨어공학",
        "professor_name": "김교수",
        "classroom": "우당관 401호",
        "day_of_week": "월",
        "start_time": "09:00:00",
        "end_time": "10:30:00",
        "user_id": 1,
        "created_at": "2024-01-15T09:00:00"
      }
    ]
  }
}
```

---

## 💬 채팅 API

### 1. 채팅방 관리

#### 📝 채팅방 생성
```http
POST /chat/rooms/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "room_name": "소프트웨어공학 스터디",
  "room_type": "group",
  "participant_ids": [2, 3, 4]
}
```

#### 📋 채팅방 목록 조회
```http
GET /chat/rooms/
Authorization: Bearer {access_token}
```

**응답 예시:**
```json
{
  "rooms": [
    {
      "room_id": 1,
      "room_name": "소프트웨어공학 스터디",
      "room_type": "group",
      "created_by": 1,
      "is_active": true,
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T15:30:00",
      "participant_count": 4,
      "last_message": "내일 과제 제출 잊지 마세요!",
      "unread_count": 3
    }
  ],
  "total_count": 1
}
```

### 2. 메시지 관리

#### 📋 채팅 메시지 조회
```http
GET /chat/rooms/{room_id}/messages/?page=1&size=50
Authorization: Bearer {access_token}
```

**응답 예시 (개선됨):**
```json
{
  "messages": [
    {
      "message_id": 1,
      "room_id": 1,
      "sender_id": 1,
      "sender_name": "홍길동",
      "message_content": "안녕하세요! 스터디 시작해볼까요?",
      "message_type": "text",
      "file_url": null,
      "file_name": null,
      "file_size": null,
      "reply_to_message_id": null,
      "reply_to_message": null,
      "is_edited": false,
      "is_deleted": false,
      "edited_at": null,
      "reactions": [
        {
          "reaction_id": 1,
          "message_id": 1,
          "user_id": 2,
          "user_name": "김철수",
          "emoji": "👍",
          "created_at": "2024-01-15T10:07:00"
        }
      ],
      "created_at": "2024-01-15T10:05:00",
      "updated_at": "2024-01-15T10:05:00"
    }
  ],
  "total_count": 15,
  "has_more": false
}
```

### 📝 메시지 타입 확장
- `text`: 텍스트 메시지
- `image`: 이미지
- `file`: 파일
- `voice`: 음성 메시지 ✨ **NEW**
- `location`: 위치 정보 ✨ **NEW**

---

## 🚀 고급 채팅 기능

### 1. 파일 업로드

#### 📎 채팅 파일 업로드
```http
POST /chat/upload/?room_id={room_id}
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: [파일 데이터]
```

**응답:**
```json
{
  "file_url": "/static/chat/files/room_1/file_123.pdf",
  "file_name": "과제_자료.pdf",
  "file_size": 1024768
}
```

### 2. 메시지 반응(이모지)

#### 👍 메시지에 반응 추가
```http
POST /chat/messages/{message_id}/reactions/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "emoji": "👍"
}
```

#### ❌ 메시지 반응 제거
```http
DELETE /chat/messages/{message_id}/reactions/{emoji}
Authorization: Bearer {access_token}
```

#### 📋 메시지 반응 목록 조회
```http
GET /chat/messages/{message_id}/reactions/
Authorization: Bearer {access_token}
```

### 3. 메시지 검색

#### 🔍 채팅방 내 메시지 검색
```http
GET /chat/rooms/{room_id}/search/?q={검색어}&page=1&size=20
Authorization: Bearer {access_token}
```

**응답:**
```json
{
  "messages": [...],
  "total_count": 25,
  "page": 1,
  "has_more": true
}
```

### 4. 채팅방 개인 설정

#### ⚙️ 채팅방 설정 조회
```http
GET /chat/rooms/{room_id}/settings/
Authorization: Bearer {access_token}
```

#### ⚙️ 채팅방 설정 업데이트
```http
PUT /chat/rooms/{room_id}/settings/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "notifications_enabled": true,
  "notification_sound": "default",
  "background_theme": "light",
  "font_size": "medium",
  "auto_download_images": true,
  "auto_download_files": false
}
```

**설정 옵션:**
- `notifications_enabled`: 알림 활성화
- `notification_sound`: 알림음 (default, sound1, sound2, etc.)
- `background_theme`: 배경 테마 (default, dark, light, custom)
- `font_size`: 글꼴 크기 (small, medium, large)
- `auto_download_images`: 이미지 자동 다운로드
- `auto_download_files`: 파일 자동 다운로드

### 5. 예약 메시지

#### ⏰ 예약 메시지 생성
```http
POST /chat/rooms/{room_id}/scheduled-messages/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message_content": "오늘 수업 잊지 마세요!",
  "message_type": "text",
  "scheduled_time": "2024-01-16T08:00:00"
}
```

### 6. 온라인 상태 조회

#### 👥 채팅방 참여자 온라인 상태
```http
GET /chat/rooms/{room_id}/online-status/
Authorization: Bearer {access_token}
```

**응답:**
```json
[
  {
    "user_id": 1,
    "user_name": "홍길동",
    "is_online": true,
    "last_seen": "2024-01-15T15:30:00",
    "status_message": "공부 중"
  },
  {
    "user_id": 2,
    "user_name": "김철수",
    "is_online": false,
    "last_seen": "2024-01-15T14:20:00",
    "status_message": null
  }
]
```

---

## 🔄 WebSocket 실시간 채팅

### 연결
```javascript
const token = localStorage.getItem('access_token');
const roomId = 1;
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}?token=${token}`);
```

### 메시지 전송 (확장됨)
```javascript
// 텍스트 메시지
ws.send(JSON.stringify({
  type: "message",
  content: "안녕하세요!",
  message_type: "text"
}));

// 답장 메시지
ws.send(JSON.stringify({
  type: "message",
  content: "네, 맞습니다!",
  message_type: "text",
  reply_to_message_id: 123
}));

// 파일 메시지
ws.send(JSON.stringify({
  type: "message",
  content: "파일을 첨부했습니다.",
  message_type: "file",
  file_url: "/static/chat/files/room_1/file_123.pdf",
  file_name: "과제_자료.pdf",
  file_size: 1024768
}));
```

### 메시지 수신 (확장됨)
```javascript
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'message':
      console.log(`${data.sender_name}: ${data.content}`);
      if (data.reply_to_message) {
        console.log(`답장: ${data.reply_to_message.content}`);
      }
      break;
      
    case 'reaction':
      console.log(`${data.user_name}님이 ${data.emoji} 반응을 ${data.action}했습니다.`);
      break;
      
    case 'join':
      console.log(`${data.sender_name}님이 입장하셨습니다.`);
      break;
      
    case 'leave':
      console.log(`${data.sender_name}님이 퇴장하셨습니다.`);
      break;
      
    case 'typing':
      console.log(`${data.sender_name}님이 입력 중입니다...`);
      break;
  }
};
```

---

## 👤 프로필 & 이미지 관리

### 1. 사용자 정보 조회 (확장됨)

#### 📋 내 정보 조회
```http
GET /auth/me
Authorization: Bearer {access_token}
```

**응답 (확장됨):**
```json
{
  "user_id": 1,
  "email": "student@kbu.ac.kr",
  "name": "홍길동",
  "birth_date": "2002-03-15",
  "gender": "M",
  "nationality": "대한민국",
  "phone_number": "010-1234-5678",
  "terms_agreed": true,
  "created_at": "2024-01-15T09:00:00",
  "department": "컴퓨터공학과",
  "student_status": "재학",
  "friend_type": "학습형",
  "smoking": "비흡연",
  "drinking": "가끔",
  "mbti": "ENFP",
  "personality_keywords": ["활발한", "창의적인"],
  "interest_keywords": ["코딩", "게임"],
  "onboarding_completed": true
}
```

### 2. 개인정보 수정

#### ✏️ 이름 수정
```http
PUT /api/users/profile
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "김홍길동"
}
```

### 3. 온보딩 프로필 관리

#### 📋 온보딩 프로필 조회
```http
GET /api/users/onboarding/profile
Authorization: Bearer {access_token}
```

#### ✏️ 온보딩 프로필 수정
```http
PUT /api/users/onboarding/profile
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "friend_type": "활동형",
  "department": "컴퓨터공학과",
  "student_status": "재학",
  "smoking": "비흡연",
  "drinking": "가끔",
  "religion": "무교",
  "mbti": "ENFP",
  "personality_keywords": ["활발한", "창의적인", "유머러스한"],
  "interest_keywords": ["코딩", "게임", "음악"],
  "friend_style_keywords": ["함께 공부하는", "운동을 좋아하는"]
}
```

### 4. 이미지 관리

#### 📷 프로필 이미지 업로드
```http
POST /api/users/images/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

images: [이미지 파일들] (최대 5장)
primary_image_index: 0
```

**응답:**
```json
{
  "message": "프로필 이미지가 성공적으로 업로드되었습니다.",
  "uploaded_images": [
    {
      "image_id": 1,
      "image_url": "/static/images/profiles/1/profile_1_1.jpg",
      "file_name": "profile1.jpg",
      "file_size": 204800,
      "is_primary": true,
      "upload_order": 1
    }
  ],
  "total_images": 1,
  "primary_image_id": 1
}
```

#### 📋 프로필 이미지 목록 조회
```http
GET /api/users/{user_id}/profile/images
Authorization: Bearer {access_token}
```

#### 🗑️ 프로필 이미지 삭제
```http
DELETE /api/users/{user_id}/profile/images/{image_id}
Authorization: Bearer {access_token}
```

#### ⭐ 대표 이미지 설정
```http
PUT /api/users/{user_id}/profile/images/{image_id}/primary
Authorization: Bearer {access_token}
```

---

## 🔔 알람 시스템

### 1. 알람 조회

#### 📋 알람 목록 조회
```http
GET /notifications/?page=1&size=20&unread_only=false
Authorization: Bearer {access_token}
```

#### 📊 알람 통계 조회
```http
GET /notifications/stats
Authorization: Bearer {access_token}
```

**응답:**
```json
{
  "total_count": 25,
  "unread_count": 8,
  "by_type": {
    "chat": 12,
    "timetable": 8,
    "match": 3,
    "system": 2,
    "reminder": 0
  }
}
```

### 2. 알람 관리

#### ✅ 알람 읽음 처리
```http
POST /notifications/mark-read
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "notification_ids": [1, 2, 3]
}
```

#### ✅ 모든 알람 읽음 처리
```http
POST /notifications/mark-all-read
Authorization: Bearer {access_token}
```

#### 🗑️ 알람 삭제
```http
DELETE /notifications/{notification_id}
Authorization: Bearer {access_token}
```

### 알람 타입
- `chat`: 채팅 메시지 알람
- `timetable`: 시간표/수업 알람
- `match`: 매칭 관련 알람
- `system`: 시스템 공지사항
- `reminder`: 사용자 리마인더

---

## 🔧 주요 개선사항

### ✨ 새로운 기능
1. **메시지 반응 시스템** - 이모지로 메시지에 반응
2. **답장 기능** - 특정 메시지에 답장 가능
3. **파일 첨부** - 이미지, 파일, 음성, 위치 정보 전송
4. **메시지 검색** - 채팅방 내 메시지 검색
5. **예약 메시지** - 특정 시간에 메시지 자동 전송
6. **채팅방 개인 설정** - 알림, 테마, 글꼴 등 개인화
7. **온라인 상태** - 실시간 온라인/오프라인 상태 표시
8. **프로필 이미지 관리** - 최대 5장, 대표 이미지 설정

### 🔄 개선된 기능
1. **유연한 데이터 타입** - Enum → String으로 변경하여 확장성 증대
2. **자동 시간표 생성** - 활성 시간표 없을 시 자동 생성
3. **확장된 사용자 정보** - 온보딩 정보 포함한 통합 조회
4. **JSON 키워드 저장** - 키워드를 JSON 배열로 저장하여 관리 효율성 증대

---

## 📱 프론트엔드 구현 팁

### 실시간 채팅 구현
```javascript
// 메시지 전송 함수
const sendMessage = (content, messageType = 'text', replyToId = null) => {
  const message = {
    type: "message",
    content: content,
    message_type: messageType,
    reply_to_message_id: replyToId
  };
  
  ws.send(JSON.stringify(message));
};

// 반응 추가 함수
const addReaction = async (messageId, emoji) => {
  try {
    const response = await fetch(`/chat/messages/${messageId}/reactions/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ emoji })
    });
    
    if (!response.ok) {
      // 이미 반응이 있으면 제거됨
      console.log('반응이 제거되었습니다.');
    }
  } catch (error) {
    console.error('반응 추가 실패:', error);
  }
};

// 파일 업로드 및 메시지 전송
const uploadAndSendFile = async (file, roomId) => {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch(`/chat/upload/?room_id=${roomId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    const fileInfo = await response.json();
    
    // 파일 메시지 전송
    sendMessage(
      `파일: ${fileInfo.file_name}`,
      file.type.startsWith('image/') ? 'image' : 'file'
    );
    
  } catch (error) {
    console.error('파일 업로드 실패:', error);
  }
};
```

---

이 가이드를 참고하여 풍부한 기능의 시간표와 채팅 시스템을 구현해보세요! 🚀✨
