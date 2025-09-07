# 🚀 매칭 앱 API 완전 가이드

## 📚 목차
1. [인증 API](#-인증-api)
2. [사용자 프로필 API](#-사용자-프로필-api)
3. [시간표 API](#-시간표-api)
4. [채팅 API](#-채팅-api)
5. [WebSocket 연결](#-websocket-연결)
6. [알림 API](#-알림-api)
7. [프론트엔드 구현 가이드](#-프론트엔드-구현-가이드)

---

## 🔐 인증 API

### 로그인
```http
POST /auth/login
Content-Type: application/json

{
  "email": "pjhh2350@kbu.ac.kr",
  "password": "password123"
}
```

**성공 응답 (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**실패 응답 (401):**
```json
{
  "detail": "이메일 또는 비밀번호가 올바르지 않습니다."
}
```

### 회원가입
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@kbu.ac.kr",
  "password": "password123",
  "name": "김학생",
  "birth_date": "1995-01-01",
  "gender": "male",
  "nationality": "한국",
  "phone_number": "010-1234-5678"
}
```

### 현재 사용자 정보 조회
```http
GET /auth/me
Authorization: Bearer {access_token}
```

**응답:**
```json
{
  "user_id": 10,
  "email": "pjhh2350@kbu.ac.kr",
  "name": "박주호",
  "birth_date": "1995-01-01",
  "gender": "male",
  "nationality": "한국",
  "phone_number": "010-1234-5678",
  "terms_agreed": true,
  "created_at": "2024-01-01T12:00:00",
  "department": "컴퓨터공학과",
  "student_status": "재학",
  "friend_type": "친구",
  "smoking": "비흡연",
  "drinking": "가끔",
  "mbti": "ENFP",
  "personality_keywords": ["활발한", "긍정적인"],
  "interest_keywords": ["게임", "영화"],
  "onboarding_completed": true
}
```

---

## 👤 사용자 프로필 API

### 온보딩 프로필 조회
```http
GET /api/users/onboarding/profile
Authorization: Bearer {access_token}
```

### 온보딩 프로필 저장/업데이트
```http
PUT /api/users/onboarding/profile
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "department": "컴퓨터공학과",
  "student_status": "재학",
  "friend_type": "친구",
  "smoking": "비흡연",
  "drinking": "가끔",
  "mbti": "ENFP",
  "personality_keywords": ["활발한", "긍정적인"],
  "interest_keywords": ["게임", "영화"],
  "friend_style_keywords": ["유머러스한", "배려심많은"]
}
```

### 프로필 이미지 업로드
```http
POST /api/users/images/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

files: [이미지 파일들] (최대 5개)
```

### 사용자 이미지 조회
```http
GET /api/users/{user_id}/profile/images
Authorization: Bearer {access_token}
```

---

## 📅 시간표 API

### 활성 시간표 조회
```http
GET /timetables/active
Authorization: Bearer {access_token}
```

**응답:**
```json
{
  "timetable_id": 1,
  "user_id": 10,
  "semester": "2024-1",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00",
  "subjects": [
    {
      "subject_id": 1,
      "subject_name": "웹프로그래밍",
      "professor": "김교수",
      "credits": 3,
      "day_of_week": "월",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "location": "공학관 101호"
    }
  ]
}
```

### 과목 등록
```http
POST /subjects/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "subject_name": "웹프로그래밍",
  "professor": "김교수",
  "credits": 3,
  "day_of_week": "월",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "location": "공학관 101호"
}
```

### 시간표에 과목 추가
```http
POST /timetables/{timetable_id}/subjects/{subject_id}
Authorization: Bearer {access_token}
```

---

## 💬 채팅 API

### 채팅방 목록 조회
```http
GET /chat/rooms/
Authorization: Bearer {access_token}
```

**응답:**
```json
[
  {
    "room_id": 8,
    "room_name": "컴공과 스터디",
    "room_type": "group",
    "created_by": 1,
    "created_at": "2024-01-01T12:00:00",
    "participant_count": 5,
    "unread_count": 3,
    "last_message": {
      "content": "안녕하세요!",
      "sender_name": "박주호",
      "sent_at": "2024-01-01T15:30:00"
    }
  }
]
```

### 채팅방 생성
```http
POST /chat/rooms/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "room_name": "새 스터디 그룹",
  "room_type": "group"
}
```

### 채팅방 메시지 조회
```http
GET /chat/rooms/{room_id}/messages/?page=1&size=50
Authorization: Bearer {access_token}
```

**응답:**
```json
{
  "messages": [
    {
      "message_id": 123,
      "room_id": 8,
      "sender_id": 10,
      "sender_name": "박주호",
      "message_content": "안녕하세요!",
      "message_type": "text",
      "file_url": null,
      "file_name": null,
      "file_size": null,
      "reply_to_message_id": null,
      "reply_to_message": null,
      "is_edited": false,
      "edited_at": null,
      "created_at": "2024-01-01T15:30:00",
      "reactions": []
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

### 채팅방 참가
```http
POST /chat/rooms/{room_id}/join
Authorization: Bearer {access_token}
```

### 파일 업로드
```http
POST /chat/upload/
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

room_id: 8
file: [파일]
```

---

## 🔌 WebSocket 연결

### 연결 URL
```
ws://localhost:8000/ws/chat/{room_id}?token={access_token}
```

### 메시지 전송 형식
```json
{
  "type": "message",
  "content": "안녕하세요!",
  "message_type": "text"
}
```

### 받는 메시지 타입들
```json
// 일반 메시지
{
  "type": "message",
  "message_id": 123,
  "room_id": 8,
  "sender_id": 10,
  "sender_name": "박주호",
  "content": "안녕하세요!",
  "message_type": "text",
  "timestamp": "2024-01-01T15:30:00"
}

// 입장 알림
{
  "type": "join",
  "room_id": 8,
  "sender_id": 10,
  "sender_name": "박주호",
  "content": "박주호님이 입장하셨습니다.",
  "timestamp": "2024-01-01T15:30:00"
}

// 퇴장 알림
{
  "type": "leave",
  "room_id": 8,
  "sender_id": 10,
  "sender_name": "박주호",
  "content": "박주호님이 퇴장하셨습니다.",
  "timestamp": "2024-01-01T15:30:00"
}

// 타이핑 상태
{
  "type": "typing",
  "room_id": 8,
  "sender_id": 10,
  "sender_name": "박주호",
  "timestamp": "2024-01-01T15:30:00"
}
```

---

## 🔔 알림 API

### 알림 목록 조회
```http
GET /notifications/?page=1&size=20&unread_only=false
Authorization: Bearer {access_token}
```

### 알림 읽음 처리
```http
POST /notifications/mark-read
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "notification_ids": [1, 2, 3]
}
```

### 모든 알림 읽음 처리
```http
POST /notifications/mark-all-read
Authorization: Bearer {access_token}
```

---

## 📱 프론트엔드 구현 가이드

### Flutter WebSocket 구현

```dart
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class ChatService {
  WebSocketChannel? _channel;
  bool _isConnected = false;
  
  Future<void> connectToRoom(int roomId, String token) async {
    try {
      final uri = Uri.parse('ws://localhost:8000/ws/chat/$roomId?token=$token');
      print('🌐 WebSocket 연결 시도: $uri');
      
      _channel = WebSocketChannel.connect(uri);
      _isConnected = true;
      
      // 연결 상태 리스너
      _channel!.stream.listen(
        (message) {
          print('📨 서버에서 받은 메시지: $message');
          _handleMessage(message);
        },
        onError: (error) {
          print('❌ WebSocket 에러: $error');
          _isConnected = false;
        },
        onDone: () {
          print('🔌 WebSocket 연결 종료');
          _isConnected = false;
        },
        cancelOnError: false, // 에러 시에도 연결 유지
      );
      
      print('✅ WebSocket 연결 완료');
      
    } catch (e) {
      print('❌ WebSocket 연결 실패: $e');
      _isConnected = false;
    }
  }
  
  Future<void> sendMessage(String content) async {
    if (!_isConnected || _channel == null) {
      print('❌ WebSocket이 연결되지 않음');
      return;
    }
    
    try {
      final message = {
        'type': 'message',
        'content': content,
        'message_type': 'text'
      };
      
      print('📤 메시지 전송: $message');
      _channel!.sink.add(jsonEncode(message));
      print('✅ 메시지 전송 완료');
      
    } catch (e) {
      print('❌ 메시지 전송 에러: $e');
    }
  }
  
  void _handleMessage(String message) {
    try {
      final data = jsonDecode(message);
      print('📨 받은 메시지 파싱: $data');
      
      // 메시지 타입에 따른 처리
      switch (data['type']) {
        case 'message':
          // 새 메시지 처리
          _handleNewMessage(data);
          break;
        case 'join':
          // 입장 알림 처리
          _handleJoinMessage(data);
          break;
        case 'leave':
          // 퇴장 알림 처리
          _handleLeaveMessage(data);
          break;
        case 'typing':
          // 타이핑 상태 처리
          _handleTypingMessage(data);
          break;
      }
    } catch (e) {
      print('❌ 메시지 파싱 에러: $e');
    }
  }
  
  void _handleNewMessage(Map<String, dynamic> data) {
    // 새 메시지를 UI에 추가
    print('💬 새 메시지: ${data['content']}');
  }
  
  void _handleJoinMessage(Map<String, dynamic> data) {
    // 입장 알림 표시
    print('👋 ${data['sender_name']}님이 입장했습니다');
  }
  
  void _handleLeaveMessage(Map<String, dynamic> data) {
    // 퇴장 알림 표시
    print('👋 ${data['sender_name']}님이 퇴장했습니다');
  }
  
  void _handleTypingMessage(Map<String, dynamic> data) {
    // 타이핑 상태 표시
    print('⌨️ ${data['sender_name']}님이 입력 중...');
  }
  
  void disconnect() {
    if (_channel != null) {
      _channel!.sink.close();
      _channel = null;
      _isConnected = false;
      print('🔌 WebSocket 연결 해제');
    }
  }
}
```

### HTTP API 호출 예시

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://localhost:8000';
  String? _token;
  
  // 로그인
  Future<Map<String, dynamic>?> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'password': password,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _token = data['access_token'];
        return data;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail']);
      }
    } catch (e) {
      print('로그인 에러: $e');
      return null;
    }
  }
  
  // 헤더 생성
  Map<String, String> _getHeaders() {
    return {
      'Content-Type': 'application/json',
      if (_token != null) 'Authorization': 'Bearer $_token',
    };
  }
  
  // 채팅방 목록 조회
  Future<List<dynamic>?> getChatRooms() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/chat/rooms/'),
        headers: _getHeaders(),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      print('채팅방 목록 조회 에러: $e');
      return null;
    }
  }
  
  // 시간표 조회
  Future<Map<String, dynamic>?> getActiveTimetable() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/timetables/active'),
        headers: _getHeaders(),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      print('시간표 조회 에러: $e');
      return null;
    }
  }
}
```

### Widget 생명주기 관리

```dart
class ChatPage extends StatefulWidget {
  final int roomId;
  
  const ChatPage({Key? key, required this.roomId}) : super(key: key);
  
  @override
  _ChatPageState createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final ChatService _chatService = ChatService();
  final TextEditingController _messageController = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  
  @override
  void initState() {
    super.initState();
    _connectToChat();
  }
  
  Future<void> _connectToChat() async {
    final token = await getStoredToken(); // SharedPreferences에서 토큰 가져오기
    if (token != null) {
      await _chatService.connectToRoom(widget.roomId, token);
    }
  }
  
  @override
  void dispose() {
    _chatService.disconnect(); // 위젯이 삭제될 때만 연결 해제
    _messageController.dispose();
    super.dispose();
  }
  
  void _sendMessage() {
    final content = _messageController.text.trim();
    if (content.isNotEmpty) {
      _chatService.sendMessage(content);
      _messageController.clear();
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('채팅방 ${widget.roomId}')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return ListTile(
                  title: Text(message['sender_name'] ?? '알 수 없음'),
                  subtitle: Text(message['content'] ?? ''),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: '메시지를 입력하세요...',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                IconButton(
                  onPressed: _sendMessage,
                  icon: Icon(Icons.send),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

---

## 🔧 중요한 체크 포인트

### 1. 토큰 관리
- 로그인 후 `access_token` 저장
- 모든 API 요청 시 `Authorization: Bearer {token}` 헤더 포함
- 토큰 만료 시 재로그인 처리

### 2. WebSocket 연결 관리
- **연결 유지**: `dispose()`에서만 WebSocket 끊기
- **에러 처리**: `cancelOnError: false`로 일시적 에러 시 연결 유지
- **상태 관리**: 연결 상태를 정확히 추적

### 3. 메시지 형식
- 서버로 보낼 때: `{"type": "message", "content": "내용", "message_type": "text"}`
- 서버에서 받을 때: 타입별로 다른 처리 (`message`, `join`, `leave`, `typing`)

### 4. 에러 처리
- HTTP 상태 코드 확인
- JSON 파싱 에러 처리
- 네트워크 에러 처리

---

## 🎯 테스트 방법

1. **로그인 테스트**: Postman이나 curl로 로그인 API 호출
2. **WebSocket 테스트**: 브라우저 개발자 도구에서 WebSocket 연결
3. **메시지 전송**: Flutter 앱에서 실제 메시지 전송 테스트

이 가이드를 따라하시면 매칭 앱의 모든 기능을 제대로 구현할 수 있습니다! 🚀
