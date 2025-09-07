# 🔧 Flutter WebSocket 연결 문제 해결 가이드

## 🚨 **현재 문제점**
- WebSocket 연결은 성공하지만 바로 끊어짐
- 메시지 전송 불가능
- 실시간 채팅 동작 안 함

## ✅ **완전한 해결책**

### 1. **ChatService 클래스 완전 수정**

```dart
import 'dart:convert';
import 'dart:async';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

class ChatService {
  WebSocketChannel? _channel;
  bool _isConnected = false;
  StreamController<Map<String, dynamic>>? _messageController;
  Timer? _heartbeatTimer;
  
  // 메시지 스트림 getter
  Stream<Map<String, dynamic>>? get messageStream => _messageController?.stream;
  
  // 연결 상태 getter
  bool get isConnected => _isConnected;

  /// 채팅방에 연결
  Future<void> connectToRoom(int roomId, String token) async {
    try {
      // 기존 연결이 있다면 먼저 끊기
      await disconnect();
      
      print('🌐 WebSocket 연결 시도: ws://localhost:8000/ws/chat/$roomId?token=$token');
      
      final uri = Uri.parse('ws://localhost:8000/ws/chat/$roomId?token=$token');
      _channel = WebSocketChannel.connect(uri);
      
      // 메시지 컨트롤러 초기화
      _messageController = StreamController<Map<String, dynamic>>.broadcast();
      
      // 연결 성공 처리
      _isConnected = true;
      print('🔗 WebSocket 연결 성공!');
      
      // 메시지 리스너 설정
      _setupMessageListener();
      
      // 하트비트 시작 (연결 유지)
      _startHeartbeat();
      
    } catch (e) {
      print('❌ WebSocket 연결 실패: $e');
      _isConnected = false;
      throw e;
    }
  }

  /// 메시지 리스너 설정
  void _setupMessageListener() {
    _channel?.stream.listen(
      (data) {
        try {
          print('📨 서버로부터 메시지 수신: $data');
          final messageData = json.decode(data);
          
          // 메시지 컨트롤러로 전송
          _messageController?.add(messageData);
          
        } catch (e) {
          print('❌ 메시지 파싱 에러: $e');
        }
      },
      onError: (error) {
        print('❌ WebSocket 에러: $error');
        _handleConnectionError();
      },
      onDone: () {
        print('🔌 WebSocket 연결 종료됨');
        _handleConnectionClosed();
      },
    );
  }

  /// 하트비트 시작 (연결 유지)
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(Duration(seconds: 30), (timer) {
      if (_isConnected && _channel != null) {
        try {
          _channel?.sink.add(json.encode({
            'type': 'heartbeat',
            'timestamp': DateTime.now().toIso8601String(),
          }));
          print('💓 하트비트 전송');
        } catch (e) {
          print('❌ 하트비트 전송 실패: $e');
          _handleConnectionError();
        }
      }
    });
  }

  /// 메시지 전송
  Future<void> sendMessage(String content, {String messageType = 'text'}) async {
    if (!_isConnected || _channel == null) {
      throw Exception('WebSocket이 연결되지 않았습니다');
    }

    try {
      final message = {
        'type': 'message',
        'content': content,
        'message_type': messageType,
        'timestamp': DateTime.now().toIso8601String(),
      };

      print('📤 메시지 전송 시도: $message');
      _channel?.sink.add(json.encode(message));
      print('✅ 메시지 전송 완료');
      
    } catch (e) {
      print('❌ 메시지 전송 실패: $e');
      throw e;
    }
  }

  /// 타이핑 상태 전송
  Future<void> sendTypingStatus(bool isTyping) async {
    if (!_isConnected || _channel == null) return;

    try {
      final typingData = {
        'type': 'typing',
        'is_typing': isTyping,
        'timestamp': DateTime.now().toIso8601String(),
      };

      _channel?.sink.add(json.encode(typingData));
      print('⌨️ 타이핑 상태 전송: $isTyping');
      
    } catch (e) {
      print('❌ 타이핑 상태 전송 실패: $e');
    }
  }

  /// 연결 에러 처리
  void _handleConnectionError() {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    print('🔄 연결 재시도 준비...');
  }

  /// 연결 종료 처리
  void _handleConnectionClosed() {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    print('🔌 WebSocket 연결이 종료되었습니다');
  }

  /// 연결 해제
  Future<void> disconnect() async {
    try {
      _isConnected = false;
      _heartbeatTimer?.cancel();
      
      await _channel?.sink.close(status.goingAway);
      _channel = null;
      
      await _messageController?.close();
      _messageController = null;
      
      print('✅ WebSocket 연결 해제 완료');
    } catch (e) {
      print('❌ 연결 해제 중 에러: $e');
    }
  }
}
```

### 2. **채팅 화면 Widget 수정**

```dart
class ChatScreen extends StatefulWidget {
  final int roomId;
  final String token;

  const ChatScreen({
    Key? key,
    required this.roomId,
    required this.token,
  }) : super(key: key);

  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with WidgetsBindingObserver {
  final ChatService _chatService = ChatService();
  final TextEditingController _messageController = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  final ScrollController _scrollController = ScrollController();
  bool _isLoading = false;
  Timer? _typingTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _connectToChat();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _disconnectFromChat();
    _messageController.dispose();
    _scrollController.dispose();
    _typingTimer?.cancel();
    super.dispose();
  }

  /// 앱 생명주기 관리
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        // 앱이 포그라운드로 돌아왔을 때 재연결
        if (!_chatService.isConnected) {
          _connectToChat();
        }
        break;
      case AppLifecycleState.paused:
      case AppLifecycleState.inactive:
        // 앱이 백그라운드로 갔을 때는 연결 유지
        break;
      case AppLifecycleState.detached:
        // 앱이 완전 종료될 때만 연결 해제
        _disconnectFromChat();
        break;
      default:
        break;
    }
  }

  /// 채팅 연결
  Future<void> _connectToChat() async {
    try {
      setState(() => _isLoading = true);
      
      await _chatService.connectToRoom(widget.roomId, widget.token);
      
      // 메시지 스트림 리스너 설정
      _chatService.messageStream?.listen(
        (messageData) {
          _handleIncomingMessage(messageData);
        },
        onError: (error) {
          print('❌ 메시지 스트림 에러: $error');
          _showErrorDialog('메시지 수신 중 오류가 발생했습니다');
        },
      );
      
      print('✅ 채팅 연결 완료');
      
    } catch (e) {
      print('❌ 채팅 연결 실패: $e');
      _showErrorDialog('채팅방 연결에 실패했습니다: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  /// 채팅 연결 해제
  Future<void> _disconnectFromChat() async {
    await _chatService.disconnect();
  }

  /// 들어오는 메시지 처리
  void _handleIncomingMessage(Map<String, dynamic> messageData) {
    setState(() {
      _messages.add(messageData);
    });
    
    // 스크롤을 맨 아래로
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  /// 메시지 전송
  Future<void> _sendMessage() async {
    final content = _messageController.text.trim();
    if (content.isEmpty) return;

    try {
      // 타이핑 상태 종료
      await _chatService.sendTypingStatus(false);
      
      // 메시지 전송
      await _chatService.sendMessage(content);
      
      // 입력창 초기화
      _messageController.clear();
      
      print('✅ 메시지 전송 성공: $content');
      
    } catch (e) {
      print('❌ 메시지 전송 실패: $e');
      _showErrorDialog('메시지 전송에 실패했습니다: $e');
    }
  }

  /// 타이핑 상태 처리
  void _onTextChanged(String text) {
    // 기존 타이머 취소
    _typingTimer?.cancel();
    
    if (text.isNotEmpty) {
      // 타이핑 시작
      _chatService.sendTypingStatus(true);
      
      // 3초 후 타이핑 상태 종료
      _typingTimer = Timer(Duration(seconds: 3), () {
        _chatService.sendTypingStatus(false);
      });
    } else {
      // 텍스트가 비어있으면 타이핑 상태 종료
      _chatService.sendTypingStatus(false);
    }
  }

  /// 에러 다이얼로그 표시
  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('오류'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('확인'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('채팅방 ${widget.roomId}'),
        actions: [
          IconButton(
            icon: Icon(_chatService.isConnected ? Icons.wifi : Icons.wifi_off),
            onPressed: () {
              if (!_chatService.isConnected) {
                _connectToChat();
              }
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // 로딩 인디케이터
          if (_isLoading)
            LinearProgressIndicator(),
          
          // 메시지 리스트
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return ListTile(
                  title: Text(message['sender_name'] ?? '알 수 없음'),
                  subtitle: Text(message['content'] ?? ''),
                  trailing: Text(message['timestamp'] ?? ''),
                );
              },
            ),
          ),
          
          // 메시지 입력창
          Container(
            padding: EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    onChanged: _onTextChanged,
                    decoration: InputDecoration(
                      hintText: '메시지를 입력하세요...',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _chatService.isConnected ? _sendMessage : null,
                  child: Text('전송'),
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

### 3. **pubspec.yaml 의존성 추가**

```yaml
dependencies:
  flutter:
    sdk: flutter
  web_socket_channel: ^2.4.0  # WebSocket 지원
  # ... 기타 의존성들
```

## 🎯 **핵심 해결 포인트**

1. **✅ WidgetsBindingObserver 사용**: 앱 생명주기 관리
2. **✅ 하트비트 구현**: 연결 유지 (30초마다)
3. **✅ 메시지 스트림 관리**: 실시간 메시지 수신
4. **✅ 에러 처리**: 연결 실패 시 적절한 처리
5. **✅ dispose 처리**: 메모리 누수 방지
6. **✅ 재연결 로직**: 연결 끊어짐 시 재연결

## 🚀 **사용 방법**

```dart
// 채팅 화면으로 이동
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => ChatScreen(
      roomId: 8,
      token: 'your_jwt_token_here',
    ),
  ),
);
```

## 📝 **주의사항**

1. **절대로 dispose에서 연결을 끊지 마세요** (앱 백그라운드 시)
2. **didChangeAppLifecycleState로 생명주기 관리**
3. **하트비트로 연결 유지**
4. **에러 발생 시 사용자에게 적절한 피드백 제공**

이제 WebSocket 연결이 안정적으로 유지되고 실시간 채팅이 정상 작동할 것입니다! 🎉
