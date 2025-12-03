from sqlalchemy import Column, Integer, String, Date, Enum, Boolean, TIMESTAMP, DateTime, Time, ForeignKey, Index, Text, Float
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
    blocked_users = relationship("UserBlock", foreign_keys="[UserBlock.blocker_id]", back_populates="blocker")
    blocked_by = relationship("UserBlock", foreign_keys="[UserBlock.blocked_id]", back_populates="blocked")
    notification_settings = relationship("UserNotificationSettings", back_populates="user", uselist=False)
    
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


class UserKeyword(Base):
    """사용자 키워드 테이블"""
    __tablename__ = "user_keywords"
    
    keyword_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    keyword_type = Column(String(50), nullable=False)  # personality, hobby, ideal_type
    keyword_value = Column(String(100), nullable=False)  # 키워드 값
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User")
    
    # 인덱스
    __table_args__ = (
        Index('idx_user_keyword', 'user_id', 'keyword_type'),
    )
    
    def __repr__(self):
        return f"<UserKeyword(keyword_id={self.keyword_id}, user_id={self.user_id}, type={self.keyword_type})>"


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

# =============================================================================
# 그룹/워크스페이스 시스템 테이블
# =============================================================================

class Group(Base):
    """그룹/워크스페이스 테이블"""
    __tablename__ = "groups"
    
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(100), nullable=False)  # 그룹 이름
    description = Column(String(500), nullable=True)  # 그룹 설명
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # 생성자
    is_public = Column(Boolean, nullable=False, default=True)  # 공개 여부
    requires_approval = Column(Boolean, nullable=False, default=False)  # 가입 승인 필요 여부
    max_members = Column(Integer, nullable=True)  # 최대 멤버 수 (None이면 제한 없음)
    is_active = Column(Boolean, nullable=False, default=True)  # 활성 상태
    
    # Phase 1 추가 필드
    view_count = Column(Integer, nullable=False, default=0)  # 조회수
    category = Column(String(50), nullable=True)  # 카테고리 (운동, 스터디, 맛집탐방, 게임, 친목, 문화, 기타)
    tags = Column(Text, nullable=True)  # 태그 (JSON 형식으로 저장: ["#독서", "#자기계발"])
    primary_image_url = Column(String(500), nullable=True)  # 대표 이미지 URL
    
    # 정규 모임 정보
    is_regular = Column(Boolean, nullable=False, default=False)  # 정규 모임 여부
    regular_weekday = Column(String(50), nullable=True)  # 정규 모임 요일 (JSON 배열: "[2,7]" = 화,일)
    regular_time = Column(Time, nullable=True)  # 정규 모임 시간
    regular_location = Column(String(200), nullable=True)  # 정규 모임 장소
    
    # 모임 규칙
    rules = Column(Text, nullable=True)  # 모임 규칙 (JSON 배열)
    
    # 활동계획
    activity_plan = Column(Text, nullable=True)  # 활동계획 (JSON 배열)
    
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("GroupMember", back_populates="group")
    posts = relationship("GroupPost", back_populates="group")
    gallery_images = relationship("GroupGallery", back_populates="group")
    meetings = relationship("GroupMeeting", back_populates="group")
    likes = relationship("GroupLike", back_populates="group")
    
    def __repr__(self):
        return f"<Group(group_id={self.group_id}, name='{self.group_name}')>"

class GroupMember(Base):
    """그룹 멤버 테이블"""
    __tablename__ = "group_members"
    
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    role = Column(Enum('owner', 'admin', 'member'), nullable=False, default='member')  # 역할
    status = Column(Enum('pending', 'approved', 'rejected'), nullable=False, default='approved')  # 가입 상태
    joined_at = Column(TIMESTAMP, default=func.current_timestamp())
    left_at = Column(TIMESTAMP, nullable=True)  # 탈퇴 시간
    is_active = Column(Boolean, nullable=False, default=True)  # 활성 상태
    
    # 관계 설정
    group = relationship("Group", back_populates="members")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_group_user', 'group_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id}, role='{self.role}')>"

class GroupPost(Base):
    """그룹 게시글 테이블"""
    __tablename__ = "group_posts"
    
    post_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(200), nullable=False)  # 제목
    content = Column(String(5000), nullable=False)  # 내용
    category = Column(String(50), nullable=True, default='일반')  # 카테고리 (공지/일반/질문/후기)
    is_pinned = Column(Boolean, nullable=False, default=False)  # 고정 여부
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    group = relationship("Group", back_populates="posts")
    author = relationship("User")
    comments = relationship("GroupPostComment", back_populates="post")
    
    # 인덱스
    __table_args__ = (
        Index('idx_group_post_created', 'group_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<GroupPost(post_id={self.post_id}, group_id={self.group_id}, title='{self.title}')>"

class GroupPostComment(Base):
    """그룹 게시글 댓글 테이블"""
    __tablename__ = "group_post_comments"
    
    comment_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('group_posts.post_id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(String(1000), nullable=False)  # 댓글 내용
    parent_comment_id = Column(Integer, ForeignKey('group_post_comments.comment_id'), nullable=True)  # 대댓글
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    post = relationship("GroupPost", back_populates="comments")
    author = relationship("User")
    parent_comment = relationship("GroupPostComment", remote_side=[comment_id])
    
    # 인덱스
    __table_args__ = (
        Index('idx_post_comment_created', 'post_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<GroupPostComment(comment_id={self.comment_id}, post_id={self.post_id})>"

class GroupGallery(Base):
    """그룹 갤러리 이미지 테이블"""
    __tablename__ = "group_gallery"
    
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    uploaded_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    image_url = Column(String(500), nullable=False)  # 이미지 URL
    file_name = Column(String(255), nullable=False)  # 원본 파일명
    file_size = Column(Integer, nullable=False)  # 파일 크기 (bytes)
    description = Column(String(500), nullable=True)  # 설명
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    group = relationship("Group", back_populates="gallery_images")
    uploader = relationship("User")
    
    # 인덱스
    __table_args__ = (
        Index('idx_group_gallery_created', 'group_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<GroupGallery(image_id={self.image_id}, group_id={self.group_id})>"

class GroupMeeting(Base):
    """그룹 정기모임 테이블"""
    __tablename__ = "group_meetings"
    
    meeting_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(200), nullable=False)  # 모임 제목
    description = Column(String(1000), nullable=True)  # 모임 설명
    meeting_date = Column(DateTime, nullable=False)  # 모임 일시
    location = Column(String(200), nullable=True)  # 장소
    max_attendees = Column(Integer, nullable=True)  # 최대 참석자 수
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    group = relationship("Group", back_populates="meetings")
    creator = relationship("User", foreign_keys=[created_by])
    attendees = relationship("GroupMeetingAttendee", back_populates="meeting")
    
    def __repr__(self):
        return f"<GroupMeeting(meeting_id={self.meeting_id}, group_id={self.group_id}, title='{self.title}')>"

class GroupMeetingAttendee(Base):
    """그룹 정기모임 참석자 테이블"""
    __tablename__ = "group_meeting_attendees"
    
    attendee_id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey('group_meetings.meeting_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    status = Column(Enum('attending', 'not_attending', 'maybe'), nullable=False, default='attending')  # 참석 상태
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    meeting = relationship("GroupMeeting", back_populates="attendees")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_meeting_user', 'meeting_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GroupMeetingAttendee(meeting_id={self.meeting_id}, user_id={self.user_id})>"

# =============================================================================
# 매칭 시스템 테이블
# =============================================================================

class MatchingRequest(Base):
    """매칭 요청 테이블"""
    __tablename__ = "matching_requests"
    
    request_id = Column(Integer, primary_key=True, autoincrement=True)
    requester_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # 요청자
    requested_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # 요청받은 사람
    status = Column(Enum('pending', 'accepted', 'rejected', 'cancelled'), nullable=False, default='pending')
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    requester = relationship("User", foreign_keys=[requester_id])
    requested = relationship("User", foreign_keys=[requested_id])
    
    # 복합 유니크 키 (같은 사람에게 중복 요청 방지)
    __table_args__ = (
        Index('idx_requester_requested', 'requester_id', 'requested_id', unique=True),
    )
    
    def __repr__(self):
        return f"<MatchingRequest(request_id={self.request_id}, requester_id={self.requester_id}, requested_id={self.requested_id})>"

class FriendRelationship(Base):
    """친구 관계 테이블"""
    __tablename__ = "friend_relationships"
    
    relationship_id = Column(Integer, primary_key=True, autoincrement=True)
    user1_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    is_active = Column(Boolean, nullable=False, default=True)  # 관계 활성 상태
    
    # 관계 설정
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_user1_user2', 'user1_id', 'user2_id', unique=True),
    )
    
    def __repr__(self):
        return f"<FriendRelationship(relationship_id={self.relationship_id}, user1_id={self.user1_id}, user2_id={self.user2_id})>"

# =============================================================================
# 사용자 차단 및 설정 테이블
# =============================================================================

class UserBlock(Base):
    """사용자 차단 테이블"""
    __tablename__ = "user_blocks"
    
    block_id = Column(Integer, primary_key=True, autoincrement=True)
    blocker_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # 차단한 사람
    blocked_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # 차단당한 사람
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    blocker = relationship("User", foreign_keys=[blocker_id], back_populates="blocked_users")
    blocked = relationship("User", foreign_keys=[blocked_id], back_populates="blocked_by")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_blocker_blocked', 'blocker_id', 'blocked_id', unique=True),
    )
    
    def __repr__(self):
        return f"<UserBlock(blocker_id={self.blocker_id}, blocked_id={self.blocked_id})>"

class GroupLike(Base):
    """그룹 좋아요 테이블"""
    __tablename__ = "group_likes"
    
    like_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    group = relationship("Group", back_populates="likes")
    user = relationship("User")
    
    # 복합 유니크 키 (한 사용자가 같은 그룹을 여러 번 좋아요 할 수 없음)
    __table_args__ = (
        Index('idx_group_user_like', 'group_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GroupLike(group_id={self.group_id}, user_id={self.user_id})>"

class UserNotificationSettings(Base):
    """사용자 알림 설정 테이블"""
    __tablename__ = "user_notification_settings"
    
    setting_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, unique=True)
    push_enabled = Column(Boolean, nullable=False, default=True)  # 푸시 알림 활성화
    chat_notifications = Column(Boolean, nullable=False, default=True)  # 채팅 알림
    timetable_notifications = Column(Boolean, nullable=False, default=True)  # 시간표 알림
    match_notifications = Column(Boolean, nullable=False, default=True)  # 매칭 알림
    system_notifications = Column(Boolean, nullable=False, default=True)  # 시스템 알림
    reminder_notifications = Column(Boolean, nullable=False, default=True)  # 리마인더 알림
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    user = relationship("User", back_populates="notification_settings")
    
    def __repr__(self):
        return f"<UserNotificationSettings(user_id={self.user_id})>"

class GroupEvent(Base):
    """그룹 이벤트/정기모임 일정 테이블"""
    __tablename__ = "group_events"
    
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    title = Column(String(200), nullable=False)  # 이벤트 제목
    description = Column(Text, nullable=True)  # 이벤트 설명
    event_date = Column(Date, nullable=False)  # 이벤트 날짜
    event_time = Column(Time, nullable=True)  # 이벤트 시간
    location = Column(String(200), nullable=True)  # 장소
    max_attendees = Column(Integer, nullable=True)  # 최대 참석자 수
    is_mandatory = Column(Boolean, nullable=False, default=False)  # 필수 참석 여부
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    group = relationship("Group", foreign_keys=[group_id])
    creator = relationship("User", foreign_keys=[created_by])
    attendances = relationship("GroupEventAttendance", back_populates="event")
    
    # 인덱스
    __table_args__ = (
        Index('idx_group_event_date', 'group_id', 'event_date'),
    )
    
    def __repr__(self):
        return f"<GroupEvent(event_id={self.event_id}, title='{self.title}')>"

class GroupEventAttendance(Base):
    """그룹 이벤트 참석 테이블"""
    __tablename__ = "group_event_attendance"
    
    attendance_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('group_events.event_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    status = Column(Enum('attending', 'not_attending', 'maybe'), nullable=False, default='attending')  # 참석 상태
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    event = relationship("GroupEvent", back_populates="attendances")
    user = relationship("User")
    
    # 복합 유니크 키 (한 사용자가 같은 이벤트에 여러 번 등록할 수 없음)
    __table_args__ = (
        Index('idx_event_user', 'event_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GroupEventAttendance(event_id={self.event_id}, user_id={self.user_id}, status='{self.status}')>"

class GalleryImageLike(Base):
    """갤러리 이미지 좋아요 테이블"""
    __tablename__ = "gallery_image_likes"
    
    like_id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('group_gallery.image_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    image = relationship("GroupGallery")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_image_user_like', 'image_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GalleryImageLike(image_id={self.image_id}, user_id={self.user_id})>"

class GalleryImageComment(Base):
    """갤러리 이미지 댓글 테이블"""
    __tablename__ = "gallery_image_comments"
    
    comment_id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('group_gallery.image_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(Text, nullable=False)  # 댓글 내용
    is_deleted = Column(Boolean, nullable=False, default=False)  # 삭제 여부
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    image = relationship("GroupGallery")
    user = relationship("User")
    
    # 인덱스
    __table_args__ = (
        Index('idx_image_comment_created', 'image_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<GalleryImageComment(comment_id={self.comment_id}, image_id={self.image_id})>"

class GroupPostLike(Base):
    """그룹 게시글 좋아요 테이블"""
    __tablename__ = "group_post_likes"
    
    like_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('group_posts.post_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    post = relationship("GroupPost")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_post_user_like', 'post_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GroupPostLike(post_id={self.post_id}, user_id={self.user_id})>"

class GroupPostImage(Base):
    """그룹 게시글 이미지 테이블"""
    __tablename__ = "group_post_images"
    
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('group_posts.post_id'), nullable=False)
    image_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)  # 표시 순서
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    post = relationship("GroupPost")
    
    # 인덱스
    __table_args__ = (
        Index('idx_post_image', 'post_id', 'display_order'),
    )
    
    def __repr__(self):
        return f"<GroupPostImage(image_id={self.image_id}, post_id={self.post_id})>"

class GroupPostCommentLike(Base):
    """그룹 게시글 댓글 좋아요 테이블"""
    __tablename__ = "group_post_comment_likes"
    
    like_id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(Integer, ForeignKey('group_post_comments.comment_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    comment = relationship("GroupPostComment")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_comment_user_like', 'comment_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<GroupPostCommentLike(comment_id={self.comment_id}, user_id={self.user_id})>"


# =============================================================================
# 구해요 (구인구직) 관련 테이블
# =============================================================================

class RecruitPost(Base):
    """구해요 게시글 테이블"""
    __tablename__ = "recruit_posts"
    
    post_id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    category = Column(String(50), nullable=False, default='전체')
    tags = Column(Text, nullable=True)  # JSON 배열
    headcount = Column(Integer, default=1)
    deadline_at = Column(DateTime, nullable=True)
    questions = Column(Text, nullable=True)  # JSON 배열
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    is_closed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    author = relationship("User", foreign_keys=[author_id])
    likes = relationship("RecruitPostLike", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("RecruitPostComment", back_populates="post", cascade="all, delete-orphan")
    applications = relationship("RecruitApplication", back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RecruitPost(post_id={self.post_id}, title='{self.title}')>"


class RecruitPostLike(Base):
    """구해요 게시글 좋아요 테이블"""
    __tablename__ = "recruit_post_likes"
    
    like_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('recruit_posts.post_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    post = relationship("RecruitPost", back_populates="likes")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_recruit_post_user_like', 'post_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<RecruitPostLike(post_id={self.post_id}, user_id={self.user_id})>"


class RecruitPostComment(Base):
    """구해요 게시글 댓글 테이블"""
    __tablename__ = "recruit_post_comments"
    
    comment_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('recruit_posts.post_id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey('recruit_post_comments.comment_id'), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    post = relationship("RecruitPost", back_populates="comments")
    author = relationship("User")
    parent = relationship("RecruitPostComment", remote_side=[comment_id], backref="replies")
    
    def __repr__(self):
        return f"<RecruitPostComment(comment_id={self.comment_id}, post_id={self.post_id})>"


class RecruitApplication(Base):
    """구해요 지원서 테이블"""
    __tablename__ = "recruit_applications"
    
    application_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('recruit_posts.post_id'), nullable=False)
    applicant_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    answers = Column(Text, nullable=False)  # JSON 배열
    status = Column(String(20), default='pending')  # pending, accepted, rejected
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    post = relationship("RecruitPost", back_populates="applications")
    applicant = relationship("User")
    
    # 복합 유니크 키 (중복 지원 방지)
    __table_args__ = (
        Index('idx_recruit_application_unique', 'post_id', 'applicant_id', unique=True),
    )
    
    def __repr__(self):
        return f"<RecruitApplication(application_id={self.application_id}, post_id={self.post_id})>"


# =============================================================================
# 장소 추천 (Place) 관련 테이블
# =============================================================================

class Place(Base):
    """장소 테이블"""
    __tablename__ = "places"
    
    place_id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    address = Column(String(500), nullable=True)
    category = Column(String(50), nullable=False, default='기타')
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    author = relationship("User", foreign_keys=[author_id])
    images = relationship("PlaceImage", back_populates="place", cascade="all, delete-orphan")
    likes = relationship("PlaceLike", back_populates="place", cascade="all, delete-orphan")
    reviews = relationship("PlaceReview", back_populates="place", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Place(place_id={self.place_id}, title='{self.title}')>"


class PlaceImage(Base):
    """장소 이미지 테이블"""
    __tablename__ = "place_images"
    
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(Integer, ForeignKey('places.place_id'), nullable=False)
    image_url = Column(String(500), nullable=False)
    upload_order = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    place = relationship("Place", back_populates="images")
    
    def __repr__(self):
        return f"<PlaceImage(image_id={self.image_id}, place_id={self.place_id})>"


class PlaceLike(Base):
    """장소 좋아요 테이블"""
    __tablename__ = "place_likes"
    
    like_id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(Integer, ForeignKey('places.place_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # 관계 설정
    place = relationship("Place", back_populates="likes")
    user = relationship("User")
    
    # 복합 유니크 키
    __table_args__ = (
        Index('idx_place_user_like', 'place_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<PlaceLike(place_id={self.place_id}, user_id={self.user_id})>"


class PlaceReview(Base):
    """장소 리뷰 테이블"""
    __tablename__ = "place_reviews"
    
    review_id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(Integer, ForeignKey('places.place_id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    content = Column(Text, nullable=False)
    visit_date = Column(Date, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 관계 설정
    place = relationship("Place", back_populates="reviews")
    author = relationship("User")
    
    def __repr__(self):
        return f"<PlaceReview(review_id={self.review_id}, place_id={self.place_id})>"