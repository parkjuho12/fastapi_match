from sqlalchemy import Column, Integer, String, Date, Enum, Boolean, TIMESTAMP, DateTime, Time, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.database import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(64), nullable=False)  # SHA-256 해시 (HEX 64자)
    salt = Column(String(32), nullable=False)           # Salt (16바이트를 HEX로 표현)
    name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(Enum('M', 'F'), nullable=False)
    nationality = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)  # 연락처 필드 추가
    terms_agreed = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    subjects = relationship("Subject", back_populates="user")
    timetables = relationship("Timetable", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, email='{self.email}', name='{self.name}')>"

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    verification_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    verification_code = Column(String(6), nullable=False)  # 6자리 인증번호
    purpose = Column(Enum('password_reset', 'email_verification'), nullable=False)
    is_used = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    def __repr__(self):
        return f"<EmailVerification(email='{self.email}', code='{self.verification_code}', purpose='{self.purpose}')>"

class Subject(Base):
    """과목 정보 테이블"""
    __tablename__ = "subjects"
    
    subject_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    subject_name = Column(String(100), nullable=False)  # 과목명 (예: 국어)
    professor_name = Column(String(100), nullable=False)  # 교수명 
    classroom = Column(String(100), nullable=False)  # 강의실 (예: 우당관 401호)
    day_of_week = Column(String(10), nullable=False)  # 요일 (더 유연하게 String으로 변경)
    start_time = Column(Time, nullable=False)  # 시작 시간 (예: 09:00)
    end_time = Column(Time, nullable=False)  # 종료 시간 (예: 09:50)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User", back_populates="subjects")
    
    def __repr__(self):
        return f"<Subject(subject_id={self.subject_id}, name='{self.subject_name}', professor='{self.professor_name}')>"

class Timetable(Base):
    """개인 시간표 테이블"""
    __tablename__ = "timetables"
    
    timetable_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    semester = Column(String(20), nullable=False)  # 학기 (예: 2024-1, 2024-2)
    year = Column(Integer, nullable=False)  # 년도
    is_active = Column(Boolean, nullable=False, default=True)  # 현재 활성 시간표 여부
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User", back_populates="timetables")
    timetable_subjects = relationship("TimetableSubject", back_populates="timetable")
    
    def __repr__(self):
        return f"<Timetable(timetable_id={self.timetable_id}, user_id={self.user_id}, semester='{self.semester}')>"

class TimetableSubject(Base):
    """시간표-과목 연결 테이블"""
    __tablename__ = "timetable_subjects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timetable_id = Column(Integer, ForeignKey('timetables.timetable_id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.subject_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    timetable = relationship("Timetable", back_populates="timetable_subjects")
    subject = relationship("Subject")
    
    def __repr__(self):
        return f"<TimetableSubject(timetable_id={self.timetable_id}, subject_id={self.subject_id})>"

class ChatRoom(Base):
    """채팅방 테이블"""
    __tablename__ = "chat_rooms"
    
    room_id = Column(Integer, primary_key=True, autoincrement=True)
    room_name = Column(String(100), nullable=False)  # 채팅방 이름
    room_type = Column(Enum('direct', 'group'), nullable=False, default='direct')  # 개인/그룹
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # 생성자
    is_active = Column(Boolean, nullable=False, default=True)  # 활성 상태
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("ChatParticipant", back_populates="chat_room")
    messages = relationship("ChatMessage", back_populates="chat_room")
    
    def __repr__(self):
        return f"<ChatRoom(room_id={self.room_id}, name='{self.room_name}', type='{self.room_type}')>"

class ChatParticipant(Base):
    """채팅방 참여자 테이블"""
    __tablename__ = "chat_participants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey('chat_rooms.room_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    joined_at = Column(TIMESTAMP, default=func.current_timestamp())
    left_at = Column(TIMESTAMP, nullable=True)  # 채팅방 나간 시간
    last_read_at = Column(TIMESTAMP, nullable=True)  # 마지막 읽은 시간
    is_active = Column(Boolean, nullable=False, default=True)  # 참여 상태
    notification_enabled = Column(Boolean, nullable=False, default=True)  # 알림 설정
    
    # 관계 설정
    chat_room = relationship("ChatRoom", back_populates="participants")
    user = relationship("User")
    
    # 복합 유니크 키 (같은 방에 같은 사용자 중복 방지)
    __table_args__ = (
        Index('idx_room_user', 'room_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<ChatParticipant(room_id={self.room_id}, user_id={self.user_id})>"

class ChatMessage(Base):
    """채팅 메시지 테이블"""
    __tablename__ = "chat_messages"
    
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey('chat_rooms.room_id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    message_content = Column(String(1000), nullable=False)  # 메시지 내용
    message_type = Column(Enum('text', 'image', 'file', 'voice', 'location'), nullable=False, default='text')  # 메시지 타입
    file_url = Column(String(500), nullable=True)  # 파일/이미지 URL
    file_name = Column(String(255), nullable=True)  # 원본 파일명
    file_size = Column(Integer, nullable=True)  # 파일 크기 (bytes)
    reply_to_message_id = Column(Integer, ForeignKey('chat_messages.message_id'), nullable=True)  # 답장 메시지 ID
    is_edited = Column(Boolean, nullable=False, default=False)  # 수정 여부
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    edited_at = Column(TIMESTAMP, nullable=True)  # 수정 시간
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")
    reply_to = relationship("ChatMessage", remote_side=[message_id])
    reactions = relationship("MessageReaction", back_populates="message")
    
    def __repr__(self):
        return f"<ChatMessage(message_id={self.message_id}, room_id={self.room_id}, sender_id={self.sender_id})>"

class MessageReaction(Base):
    """메시지 반응(이모지) 테이블"""
    __tablename__ = "message_reactions"
    
    reaction_id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('chat_messages.message_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    emoji = Column(String(10), nullable=False)  # 이모지 (👍, ❤️, 😂 등)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    message = relationship("ChatMessage", back_populates="reactions")
    user = relationship("User")
    
    # 복합 유니크 키 (같은 메시지에 같은 사용자는 같은 이모지 하나만)
    __table_args__ = (
        Index('idx_message_user_emoji', 'message_id', 'user_id', 'emoji', unique=True),
    )
    
    def __repr__(self):
        return f"<MessageReaction(message_id={self.message_id}, user_id={self.user_id}, emoji='{self.emoji}')>"

class ChatRoomSettings(Base):
    """채팅방 개인 설정 테이블"""
    __tablename__ = "chat_room_settings"
    
    setting_id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey('chat_rooms.room_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    notifications_enabled = Column(Boolean, nullable=False, default=True)  # 알림 활성화
    notification_sound = Column(String(50), nullable=False, default='default')  # 알림음
    background_theme = Column(String(50), nullable=False, default='default')  # 배경 테마
    font_size = Column(Enum('small', 'medium', 'large'), nullable=False, default='medium')  # 글꼴 크기
    auto_download_images = Column(Boolean, nullable=False, default=True)  # 이미지 자동 다운로드
    auto_download_files = Column(Boolean, nullable=False, default=False)  # 파일 자동 다운로드
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    chat_room = relationship("ChatRoom")
    user = relationship("User")
    
    # 복합 유니크 키 (채팅방당 사용자별 설정 하나)
    __table_args__ = (
        Index('idx_room_user_settings', 'room_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<ChatRoomSettings(room_id={self.room_id}, user_id={self.user_id})>"

class ScheduledMessage(Base):
    """예약 메시지 테이블"""
    __tablename__ = "scheduled_messages"
    
    scheduled_id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey('chat_rooms.room_id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    message_content = Column(String(1000), nullable=False)
    message_type = Column(Enum('text', 'image', 'file', 'voice', 'location'), nullable=False, default='text')
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    scheduled_time = Column(TIMESTAMP, nullable=False)  # 전송 예정 시간
    is_sent = Column(Boolean, nullable=False, default=False)  # 전송 완료 여부
    sent_at = Column(TIMESTAMP, nullable=True)  # 실제 전송 시간
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    chat_room = relationship("ChatRoom")
    sender = relationship("User")
    
    def __repr__(self):
        return f"<ScheduledMessage(scheduled_id={self.scheduled_id}, room_id={self.room_id}, sender_id={self.sender_id})>"

class UserOnlineStatus(Base):
    """사용자 온라인 상태 테이블"""
    __tablename__ = "user_online_status"
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    is_online = Column(Boolean, nullable=False, default=False)
    last_seen = Column(TIMESTAMP, nullable=False, default=func.current_timestamp())
    status_message = Column(String(100), nullable=True)  # 상태 메시지
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserOnlineStatus(user_id={self.user_id}, is_online={self.is_online})>"

# =============================================================================
# 온보딩 관련 테이블들
# =============================================================================

class UserProfile(Base):
    """사용자 온보딩 프로필 테이블"""
    __tablename__ = "user_profiles"
    
    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, unique=True)
    friend_type = Column(String(100), nullable=False)  # 자유로운 친구 유형
    department = Column(String(100), nullable=False)  # 학과
    student_status = Column(String(50), nullable=False)  # 자유로운 재학상태
    smoking = Column(String(50), nullable=False)  # 자유로운 흡연 상태
    drinking = Column(String(50), nullable=False)  # 자유로운 음주 상태
    religion = Column(String(50), nullable=True)  # 종교 (선택사항)
    mbti = Column(String(4), nullable=False)  # ENFP 형태
    
    # 키워드 필드들 (JSON 형태로 저장)
    personality_keywords = Column(String(1000), nullable=True)  # 성격 키워드 (JSON 배열)
    interest_keywords = Column(String(1000), nullable=True)     # 관심사 키워드 (JSON 배열)
    friend_style_keywords = Column(String(1000), nullable=True) # 친구 스타일 키워드 (JSON 배열)
    
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    onboarding_completed_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile(profile_id={self.profile_id}, user_id={self.user_id}, friend_type='{self.friend_type}')>"



class UserImage(Base):
    """사용자 프로필 이미지 테이블"""
    __tablename__ = "user_images"
    
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    image_url = Column(String(500), nullable=False)  # 이미지 파일 경로/URL
    is_primary = Column(Boolean, nullable=False, default=False)  # 대표 이미지 여부
    upload_order = Column(Integer, nullable=False)  # 업로드 순서 (1-6)
    file_name = Column(String(255), nullable=False)  # 원본 파일명
    file_size = Column(Integer, nullable=False)  # 파일 크기 (bytes)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정 - UserProfile과는 user_id로 연결됨
    
    # 인덱스
    __table_args__ = (
        Index('idx_user_image_order', 'user_id', 'upload_order'),
        Index('idx_user_primary', 'user_id', 'is_primary'),
    )
    
    def __repr__(self):
        return f"<UserImage(image_id={self.image_id}, user_id={self.user_id}, order={self.upload_order})>"

# =============================================================================
# 알람 시스템 테이블
# =============================================================================

class Notification(Base):
    """사용자 알람 테이블"""
    __tablename__ = "notifications"
    
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(200), nullable=False)  # 알람 제목
    message = Column(String(1000), nullable=False)  # 알람 내용
    notification_type = Column(Enum('chat', 'timetable', 'match', 'system', 'reminder'), nullable=False)  # 알람 타입
    is_read = Column(Boolean, nullable=False, default=False)  # 읽음 여부
    read_at = Column(TIMESTAMP, nullable=True)  # 읽은 시간
    data = Column(String(500), nullable=True)  # 추가 데이터 (JSON 형태, 선택사항)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User")
    
    # 인덱스
    __table_args__ = (
        Index('idx_user_notifications', 'user_id', 'created_at'),
        Index('idx_user_unread', 'user_id', 'is_read'),
    )
    
    def __repr__(self):
        return f"<Notification(notification_id={self.notification_id}, user_id={self.user_id}, type='{self.notification_type}')>"