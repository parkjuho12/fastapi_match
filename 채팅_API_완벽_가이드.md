# 🚀 채팅 시스템 API 완벽 가이드

## 📋 목차
1. [API 개요](#api-개요)
2. [인증](#인증)
3. [채팅방 관리](#채팅방-관리)
4. [메시지 관리](#메시지-관리)
5. [실시간 채팅 (WebSocket)](#실시간-채팅-websocket)
6. [고급 기능](#고급-기능)
7. [Flutter 구현 예제](#flutter-구현-예제)
8. [에러 처리](#에러-처리)

---

## 🎯 API 개요

### Base URL
```
http://localhost:8000
```

### 주요 엔드포인트 
- 채팅방 관리: `/chat/rooms/`
- 메시지 관리: `/chat/rooms/{room_id}/messages/`
- 실시간 채팅: `ws://localhost:8000/chat/ws/{room_id}`

---

## 🔐 인증

모든 API는 JWT 토큰 인증이 필요합니다.

### Headers
```json
{
  "Authorization": "Bearer YOUR_JWT_TOKEN",
  "Content-Type": "application/json"
}
```

---

## 🏠 채팅방 관리

### 1. 채팅방 목록 조회
**GET** `/chat/rooms/`

사용자가 참여한 모든 채팅방을 조회합니다.

#### 응답 예시
```json
{
  "rooms": [
    {
      "room_id": 8,
      "room_name": "김철수",
      "room_type": "direct",
      "created_by": 10,
      "is_active": true,
      "created_at": "2025-09-02T11:03:17",
      "updated_at": "2025-09-02T11:03:17",
      "participant_count": 2,
      "last_message": "안녕하세요! 반갑습니다 😊",
      "unread_count": 1
    }
  ],
  "total_count": 1
}
```

### 2. 새 채팅방 생성
**POST** `/chat/rooms/`

#### 요청 예시
```json
{
  "room_name": "새로운 채팅방",
  "room_type": "direct",
  "room_description": "채팅방 설명 (선택사항)",
  "participant_ids": [11, 12]
}
```

#### 응답 예시
```json
{
  "room_id": 9,
  "room_name": "새로운 채팅방",
  "room_type": "direct",
  "created_by": 10,
  "is_active": true,
  "created_at": "2025-09-02T12:00:00",
  "updated_at": "2025-09-02T12:00:00",
  "participant_count": 2,
  "last_message": null,
  "unread_count": 0
}
```

### 3. 채팅방 정보 조회
**GET** `/chat/rooms/{room_id}/`

#### 응답 예시
```json
{
  "room_id": 8,
  "room_name": "김철수",
  "room_type": "direct",
  "room_description": null,
  "max_participants": 100,
  "created_by": 10,
  "is_active": true,
  "created_at": "2025-09-02T11:03:17",
  "updated_at": "2025-09-02T11:03:17"
}
```

### 4. 채팅방 참여자 목록
**GET** `/chat/rooms/{room_id}/participants/`

#### 응답 예시
```json
{
  "participants": [
    {
      "id": 1,
      "room_id": 8,
      "user_id": 10,
      "user_name": "박주호",
      "joined_at": "2025-09-02T11:03:17",
      "last_read_at": "2025-09-02T11:03:17",
      "is_active": true
    },
    {
      "id": 2,
      "room_id": 8,
      "user_id": 11,
      "user_name": "김철수",
      "joined_at": "2025-09-02T11:03:17",
      "last_read_at": null,
      "is_active": true
    }
  ],
  "total_count": 2
}
```

---

## 💬 메시지 관리

### 1. 메시지 목록 조회
**GET** `/chat/rooms/{room_id}/messages/`

#### 쿼리 파라미터
- `page`: 페이지 번호 (기본값: 1)
- `size`: 페이지 크기 (기본값: 50)

#### 응답 예시
```json
{
  "messages": [
    {
      "message_id": 1,
      "room_id": 8,
      "sender_id": 11,
      "sender_name": "김철수",
      "message_content": "안녕하세요! 반갑습니다 😊",
      "message_type": "text",
      "file_url": null,
      "file_name": null,
      "file_size": null,
      "reply_to_message_id": null,
      "is_edited": false,
      "is_deleted": false,
      "edited_at": null,
      "created_at": "2025-09-02T11:05:30",
      "updated_at": "2025-09-02T11:05:30"
    }
  ],
  "total_count": 1,
  "has_more": false
}
```

### 2. 메시지 전송
**POST** `/chat/rooms/{room_id}/messages/`

#### 텍스트 메시지 요청
```json
{
  "message_content": "안녕하세요!",
  "message_type": "text"
}
```

#### 파일 메시지 요청 (multipart/form-data)
```
POST /chat/rooms/8/messages/
Content-Type: multipart/form-data

message_content: "사진을 보내드려요"
message_type: "image"
file: [파일 데이터]
```

#### 답장 메시지 요청
```json
{
  "message_content": "답장입니다!",
  "message_type": "text",
  "reply_to_message_id": 1
}
```

### 3. 메시지 수정
**PUT** `/chat/rooms/{room_id}/messages/{message_id}/`

#### 요청 예시
```json
{
  "message_content": "수정된 메시지입니다"
}
```

### 4. 메시지 삭제
**DELETE** `/chat/rooms/{room_id}/messages/{message_id}/`

### 5. 메시지 읽음 처리
**POST** `/chat/rooms/{room_id}/read/`

사용자가 채팅방의 메시지를 읽었음을 표시합니다.

---

## 🔄 실시간 채팅 (WebSocket)

### WebSocket 연결
```
ws://localhost:8000/chat/ws/{room_id}?token=YOUR_JWT_TOKEN
```

### 메시지 전송
```json
{
  "type": "message",
  "content": "안녕하세요!",
  "message_type": "text"
}
```

### 메시지 수신
```json
{
  "type": "message",
  "message_id": 123,
  "sender_id": 11,
  "sender_name": "김철수",
  "content": "안녕하세요!",
  "message_type": "text",
  "timestamp": "2025-09-02T12:00:00",
  "reply_to_message_id": null
}
```

### 타이핑 상태 전송
```json
{
  "type": "typing",
  "is_typing": true
}
```

### 타이핑 상태 수신
```json
{
  "type": "typing",
  "user_id": 11,
  "user_name": "김철수",
  "is_typing": true
}
```

### 접속 상태 알림
```json
{
  "type": "user_status",
  "user_id": 11,
  "user_name": "김철수",
  "status": "online"
}
```

---

## 🔍 고급 기능

### 1. 메시지 검색
**GET** `/chat/rooms/{room_id}/search/`

#### 쿼리 파라미터
- `query`: 검색어 (필수)
- `page`: 페이지 번호 (기본값: 1)
- `size`: 페이지 크기 (기본값: 20)

#### 응답 예시
```json
{
  "messages": [
    {
      "message_id": 1,
      "sender_name": "김철수",
      "message_content": "안녕하세요! 반갑습니다",
      "created_at": "2025-09-02T11:05:30",
      "highlight": "안녕하세요"
    }
  ],
  "total_count": 1,
  "has_more": false
}
```

### 2. 채팅방 설정
**GET** `/chat/rooms/{room_id}/settings/`

#### 응답 예시
```json
{
  "room_id": 8,
  "notification_enabled": true,
  "message_retention_days": 365,
  "auto_delete_enabled": false,
  "read_receipt_enabled": true
}
```

### 3. 채팅방 설정 업데이트
**PUT** `/chat/rooms/{room_id}/settings/`

#### 요청 예시
```json
{
  "notification_enabled": false,
  "read_receipt_enabled": true
}
```

### 4. 온라인 사용자 상태
**GET** `/chat/rooms/{room_id}/online-status/`

#### 응답 예시
```json
[
  {
    "user_id": 10,
    "user_name": "박주호",
    "is_online": true,
    "last_seen": "2025-09-02T12:00:00"
  },
  {
    "user_id": 11,
    "user_name": "김철수",
    "is_online": false,
    "last_seen": "2025-09-02T11:30:00"
  }
]
```

---

## 📱 Flutter 구현 예제

### 1. 채팅방 목록 조회
```dart
class ChatService {
  static const String baseUrl = 'http://localhost:8000';
  
  Future<ChatRoomListResponse> getChatRooms() async {
    final token = await _getToken();
    
    final response = await http.get(
      Uri.parse('$baseUrl/chat/rooms/'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
    
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = json.decode(response.body);
      return ChatRoomListResponse.fromJson(data);
    } else {
      throw Exception('채팅방 목록 조회 실패');
    }
  }
}
```

### 2. WebSocket 연결
```dart
class ChatWebSocket {
  IOWebSocketChannel? _channel;
  
  void connect(int roomId, String token) {
    _channel = IOWebSocketChannel.connect(
      'ws://localhost:8000/chat/ws/$roomId?token=$token',
    );
    
    _channel!.stream.listen(
      (message) {
        final data = json.decode(message);
        _handleMessage(data);
      },
      onError: (error) {
        print('WebSocket 에러: $error');
      },
      onDone: () {
        print('WebSocket 연결 종료');
      },
    );
  }
  
  void sendMessage(String content) {
    if (_channel != null) {
      final message = {
        'type': 'message',
        'content': content,
        'message_type': 'text',
      };
      _channel!.sink.add(json.encode(message));
    }
  }
  
  void _handleMessage(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'message':
        // 새 메시지 처리
        break;
      case 'typing':
        // 타이핑 상태 처리
        break;
      case 'user_status':
        // 사용자 상태 처리
        break;
    }
  }
  
  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }
}
```

### 3. 메시지 전송
```dart
Future<void> sendMessage(int roomId, String content) async {
  final token = await _getToken();
  
  final response = await http.post(
    Uri.parse('$baseUrl/chat/rooms/$roomId/messages/'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
    body: json.encode({
      'message_content': content,
      'message_type': 'text',
    }),
  );
  
  if (response.statusCode == 201) {
    print('메시지 전송 성공');
  } else {
    throw Exception('메시지 전송 실패');
  }
}
```

### 4. 파일 업로드
```dart
Future<void> sendFileMessage(int roomId, File file, String content) async {
  final token = await _getToken();
  
  final request = http.MultipartRequest(
    'POST',
    Uri.parse('$baseUrl/chat/rooms/$roomId/messages/'),
  );
  
  request.headers['Authorization'] = 'Bearer $token';
  request.fields['message_content'] = content;
  request.fields['message_type'] = 'image';
  
  request.files.add(
    await http.MultipartFile.fromPath('file', file.path),
  );
  
  final response = await request.send();
  
  if (response.statusCode == 201) {
    print('파일 메시지 전송 성공');
  } else {
    throw Exception('파일 메시지 전송 실패');
  }
}
```

---

## ⚠️ 에러 처리

### 일반적인 HTTP 상태 코드
- **200**: 성공
- **201**: 생성 성공
- **400**: 잘못된 요청
- **401**: 인증 실패
- **403**: 권한 없음
- **404**: 리소스 없음
- **422**: 유효성 검사 실패
- **500**: 서버 오류

### 에러 응답 형식
```json
{
  "detail": "에러 메시지"
}
```

### Flutter 에러 처리 예제
```dart
try {
  final rooms = await chatService.getChatRooms();
  // 성공 처리
} on HttpException catch (e) {
  if (e.message.contains('401')) {
    // 토큰 만료, 재로그인 필요
    await _refreshToken();
  } else if (e.message.contains('404')) {
    // 채팅방 없음
    showDialog(context: context, builder: (context) => 
      AlertDialog(title: Text('채팅방을 찾을 수 없습니다')));
  }
} catch (e) {
  // 기타 에러 처리
  print('에러: $e');
}
```

---

## 🎯 주요 사용 시나리오

### 1. 1:1 채팅 시작하기
1. 상대방과의 기존 채팅방 확인
2. 없으면 새 채팅방 생성
3. WebSocket 연결
4. 메시지 주고받기

### 2. 그룹 채팅 만들기
1. 여러 참여자와 그룹 채팅방 생성
2. 참여자들에게 알림 전송
3. WebSocket으로 실시간 채팅

### 3. 파일 공유하기
1. 파일 선택
2. multipart/form-data로 업로드
3. 파일 URL 메시지로 전송

---

## 📝 참고 사항

### 메시지 타입
- `text`: 일반 텍스트
- `image`: 이미지 파일
- `file`: 일반 파일
- `voice`: 음성 메시지 (향후 지원)
- `location`: 위치 정보 (향후 지원)

### 채팅방 타입
- `direct`: 1:1 채팅
- `group`: 그룹 채팅

### WebSocket 이벤트 타입
- `message`: 새 메시지
- `typing`: 타이핑 상태
- `user_status`: 사용자 접속 상태
- `message_read`: 메시지 읽음 상태

---

이 가이드를 참고하여 채팅 기능을 구현하시면 됩니다! 🚀
