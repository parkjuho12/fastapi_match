# Phase 2: 정기모임 시스템 구현 완료 ✅

## 📋 구현된 API (8개)

### 1. 정기모임 생성
```
POST /groups/{group_id}/meetings/
```
**권한**: owner 또는 admin만 가능

**요청**: `GroupMeetingCreate`
```json
{
  "title": "정기 스터디 모임",
  "description": "매주 월요일 스터디 모임입니다",
  "meeting_date": "2024-01-15T19:00:00",
  "location": "경복대학교 도서관 3층",
  "max_attendees": 10
}
```

**응답**: `GroupMeetingResponse`
```json
{
  "meeting_id": 1,
  "group_id": 1,
  "created_by": 1,
  "creator_name": "홍길동",
  "title": "정기 스터디 모임",
  "description": "매주 월요일 스터디 모임입니다",
  "meeting_date": "2024-01-15T19:00:00",
  "location": "경복대학교 도서관 3층",
  "max_attendees": 10,
  "attendee_count": 0,
  "created_at": "2024-01-08T16:00:00",
  "updated_at": "2024-01-08T16:00:00"
}
```

---

### 2. 정기모임 목록 조회
```
GET /groups/{group_id}/meetings/?skip=0&limit=50
```
**권한**: 
- 공개 그룹: 누구나
- 비공개 그룹: 멤버만

**응답**: `GroupMeetingListResponse`
```json
{
  "meetings": [
    {
      "meeting_id": 1,
      "group_id": 1,
      "created_by": 1,
      "creator_name": "홍길동",
      "title": "정기 스터디 모임",
      "description": "매주 월요일 스터디 모임입니다",
      "meeting_date": "2024-01-15T19:00:00",
      "location": "경복대학교 도서관 3층",
      "max_attendees": 10,
      "attendee_count": 5,
      "created_at": "2024-01-08T16:00:00",
      "updated_at": "2024-01-08T16:00:00"
    }
  ],
  "total_count": 1
}
```

**특징**:
- 최신 모임 순으로 정렬
- 페이지네이션 지원
- 참석자 수 자동 계산

---

### 3. 정기모임 상세 조회
```
GET /groups/{group_id}/meetings/{meeting_id}
```

**응답**: `GroupMeetingResponse` (위와 동일)

---

### 4. 정기모임 수정
```
PUT /groups/{group_id}/meetings/{meeting_id}
```
**권한**: 생성자 또는 관리자(owner, admin)

**요청**: `GroupMeetingUpdate`
```json
{
  "title": "정기 스터디 모임 (장소 변경)",
  "location": "경복대학교 도서관 4층"
}
```

**특징**: 필드별 부분 업데이트 가능

---

### 5. 정기모임 삭제
```
DELETE /groups/{group_id}/meetings/{meeting_id}
```
**권한**: 생성자 또는 관리자(owner, admin)

**응답**:
```json
{
  "message": "정기모임이 삭제되었습니다."
}
```

**특징**: 소프트 삭제 (is_deleted = True)

---

### 6. 참석 신청
```
POST /groups/{group_id}/meetings/{meeting_id}/attend
```
**권한**: 그룹 멤버만

**응답**:
```json
{
  "message": "참석 신청이 완료되었습니다."
}
```

**특징**:
- 최대 참석자 수 확인
- 이미 신청한 경우 상태 업데이트
- 중복 신청 방지

---

### 7. 참석 취소
```
DELETE /groups/{group_id}/meetings/{meeting_id}/attend
```

**응답**:
```json
{
  "message": "참석이 취소되었습니다."
}
```

**특징**: 삭제하지 않고 상태를 'not_attending'으로 변경

---

### 8. 참석자 목록 조회
```
GET /groups/{group_id}/meetings/{meeting_id}/attendees
```

**응답**:
```json
{
  "attendees": [
    {
      "user_id": 1,
      "user_name": "홍길동",
      "email": "user1@kbu.ac.kr",
      "status": "attending",
      "joined_at": "2024-01-08T16:05:00"
    }
  ],
  "total_count": 1
}
```

**특징**: 참석 확정(attending) 상태만 조회

---

## 🎯 주요 기능

### ✅ 권한 관리
- **생성/수정/삭제**: owner 또는 admin만 가능
- **참석 신청**: 그룹 멤버만 가능
- **조회**: 공개 그룹은 누구나, 비공개는 멤버만

### ✅ 참석자 관리
- 최대 참석자 수 제한 (`max_attendees`)
- 참석 상태: `pending`, `attending`, `not_attending`
- 중복 신청 방지
- 참석자 수 자동 계산

### ✅ 데이터 무결성
- 소프트 삭제 (`is_deleted`)
- 타임스탬프 자동 관리
- 중복 참석 방지 (unique index)

---

## 🔧 데이터베이스 테이블

### group_meetings
```sql
CREATE TABLE group_meetings (
    meeting_id INT PRIMARY KEY AUTO_INCREMENT,
    group_id INT NOT NULL,
    created_by INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    meeting_date DATETIME NOT NULL,
    location VARCHAR(200),
    max_attendees INT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### group_meeting_attendees
```sql
CREATE TABLE group_meeting_attendees (
    attendee_id INT PRIMARY KEY AUTO_INCREMENT,
    meeting_id INT NOT NULL,
    user_id INT NOT NULL,
    status ENUM('pending', 'attending', 'not_attending') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (meeting_id, user_id)
);
```

---

## 📱 Flutter 연동 예시

### 1. 정기모임 목록 조회
```dart
Future<void> loadMeetings() async {
  final response = await ApiService.getGroupMeetings(groupId: groupId);
  
  setState(() {
    meetings = response['meetings'];
    totalCount = response['total_count'];
  });
}
```

### 2. 정기모임 생성
```dart
Future<void> createMeeting() async {
  await ApiService.createGroupMeeting(
    groupId: groupId,
    title: "정기 스터디",
    description: "매주 월요일",
    meetingDate: DateTime(2024, 1, 15, 19, 0),
    location: "도서관 3층",
    maxAttendees: 10,
  );
  
  loadMeetings(); // 목록 새로고침
}
```

### 3. 참석 신청
```dart
Future<void> attendMeeting(int meetingId) async {
  await ApiService.attendGroupMeeting(
    groupId: groupId,
    meetingId: meetingId,
  );
  
  loadMeetings(); // 참석자 수 업데이트
}
```

### 4. 참석자 목록 조회
```dart
Future<void> loadAttendees(int meetingId) async {
  final response = await ApiService.getMeetingAttendees(
    groupId: groupId,
    meetingId: meetingId,
  );
  
  setState(() {
    attendees = response['attendees'];
  });
}
```

---

## 🧪 테스트 시나리오

### 1️⃣ 정기모임 생성 (관리자)
```bash
curl -X POST http://localhost:8000/groups/1/meetings/ \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "주간 스터디",
    "description": "매주 월요일 스터디",
    "meeting_date": "2024-01-15T19:00:00",
    "location": "도서관 3층",
    "max_attendees": 10
  }'
```

### 2️⃣ 정기모임 목록 조회
```bash
curl -X GET http://localhost:8000/groups/1/meetings/ \
  -H "Authorization: Bearer {token}"
```

### 3️⃣ 참석 신청 (멤버)
```bash
curl -X POST http://localhost:8000/groups/1/meetings/1/attend \
  -H "Authorization: Bearer {member_token}"
```

### 4️⃣ 참석자 목록 확인
```bash
curl -X GET http://localhost:8000/groups/1/meetings/1/attendees \
  -H "Authorization: Bearer {token}"
```

### 5️⃣ 참석 취소
```bash
curl -X DELETE http://localhost:8000/groups/1/meetings/1/attend \
  -H "Authorization: Bearer {member_token}"
```

### 6️⃣ 정기모임 수정 (관리자)
```bash
curl -X PUT http://localhost:8000/groups/1/meetings/1 \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "도서관 4층"
  }'
```

### 7️⃣ 정기모임 삭제 (관리자)
```bash
curl -X DELETE http://localhost:8000/groups/1/meetings/1 \
  -H "Authorization: Bearer {admin_token}"
```

---

## ⚠️ 주의사항

### 1. 권한 체계
- **생성/수정/삭제**: owner 또는 admin 필요
- **참석 신청**: 일반 멤버도 가능
- **조회**: 비공개 그룹은 멤버만

### 2. 참석자 관리
- `max_attendees`가 설정된 경우 인원 제한
- 중복 참석 방지 (unique constraint)
- 참석 취소 시 삭제가 아닌 상태 변경

### 3. 소프트 삭제
- 정기모임 삭제 시 `is_deleted = True`
- 조회 시 자동으로 제외됨
- 복구 기능 추가 가능

---

## 📊 통계

- **구현된 API**: 8개
- **데이터베이스 테이블**: 2개 (이미 존재함)
- **스키마**: 이미 존재함
- **구현 시간**: 약 2시간
- **코드 라인**: 약 580줄

---

## 🎉 완료 사항

### Phase 1
- ✅ 갤러리 시스템 (3개 API)
- ✅ 그룹 멤버 역할 변경 (1개 API)
- ✅ 매칭 수락 시 채팅방 자동 생성

### Phase 2 ⭐ NEW
- ✅ 정기모임 관리 시스템 (8개 API)

**총 구현 API**: 12개 (Phase 1: 4개, Phase 2: 8개)

---

## 🔜 다음 단계

### 옵션 A: Flutter 더미 데이터 제거 (권장)
- 채팅 메시지 목록 (API 있음)
- 보낸 매칭 요청 (API 있음)
- 게시글 댓글 (API 있음)
- 예상 시간: 3시간

### 옵션 B: 추가 백엔드 기능
- 갤러리 좋아요/댓글 (2시간)
- 그룹 추가 필드 (1시간)
- 구인구직 시스템 (5-6시간)

---

**작성일**: 2024년 1월 8일  
**버전**: 2.0  
**구현 시간**: 2시간  
**상태**: ✅ 구현 완료, 테스트 대기

