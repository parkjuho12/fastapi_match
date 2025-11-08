from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date, datetime, time
from typing import Optional, List
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "M"
    FEMALE = "F"

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    birth_date: date
    gender: GenderEnum
    nationality: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20, description="연락처")
    terms_agreed: bool = Field(..., description="이용약관 동의 여부")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="최소 8자 이상의 비밀번호")
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v):
        if not str(v).endswith('@kbu.ac.kr'):
            raise ValueError('경복대학교 이메일(@kbu.ac.kr)만 사용할 수 있습니다.')
        return v
    
    @field_validator('terms_agreed')
    @classmethod
    def terms_must_be_agreed(cls, v):

        if not v:
            raise ValueError('이용약관에 동의해야 합니다.')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        
        # 영문, 숫자, 특수문자 중 2가지 이상 포함 검증
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        count = sum([has_letter, has_digit, has_special])
        if count < 2:
            raise ValueError('비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 포함해야 합니다.')
        
        return v

class UserResponse(UserBase):
    user_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

# 개인정보 수정용 스키마
class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="이름")

# 확장된 사용자 정보 응답 스키마
class UserMeResponse(UserBase):
    user_id: int
    created_at: datetime
    
    # 온보딩 정보들
    department: Optional[str] = Field(None, description="학과")
    student_status: Optional[str] = Field(None, description="재학상태")
    friend_type: Optional[str] = Field(None, description="친구 유형")
    smoking: Optional[str] = Field(None, description="흡연 여부")
    drinking: Optional[str] = Field(None, description="음주 여부")
    mbti: Optional[str] = Field(None, description="MBTI")
    personality_keywords: List[str] = Field([], description="성격 키워드")
    interest_keywords: List[str] = Field([], description="관심사 키워드")
    onboarding_completed: bool = Field(False, description="온보딩 완료 여부")
    
    model_config = {"from_attributes": True}



class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# 아이디 찾기 관련 스키마
class FindUserIdRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="이름")
    birth_date: date = Field(..., description="생년월일")
    phone_number: str = Field(..., min_length=1, max_length=20, description="연락처")

class FindUserIdResponse(BaseModel):
    email: str = Field(..., description="찾은 이메일(아이디)")
    name: str = Field(..., description="이름")
    created_at: datetime = Field(..., description="가입일")

# 비밀번호 찾기 관련 스키마
class PasswordResetRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100, description="가입 시 등록한 이름")

class VerificationCodeRequest(BaseModel):
    email: EmailStr
    verification_code: str

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    verification_code: str
    new_password: str = Field(..., min_length=8, description="새로운 비밀번호 (최소 8자)")
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        
        # 영문, 숫자, 특수문자 중 2가지 이상 포함 검증
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        count = sum([has_letter, has_digit, has_special])
        if count < 2:
            raise ValueError('비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 포함해야 합니다.')
        
        return v

# 이메일 인증 관련 스키마
class EmailVerificationRequest(BaseModel):
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v):
        if not str(v).endswith('@kbu.ac.kr'):
            raise ValueError('경복대학교 이메일(@kbu.ac.kr)만 사용할 수 있습니다.')
        return v

class EmailVerificationConfirm(BaseModel):
    email: EmailStr
    verification_code: str

class UserCreateWithVerification(UserCreate):
    verification_code: str = Field(..., description="이메일 인증번호")

# 시간표 관련 Enums
class DayOfWeekEnum(str, Enum):
    MONDAY = "월"
    TUESDAY = "화"
    WEDNESDAY = "수"
    THURSDAY = "목"
    FRIDAY = "금"
    SATURDAY = "토"
    SUNDAY = "일"

# 과목 관련 스키마
class SubjectBase(BaseModel):
    subject_name: str = Field(..., min_length=1, max_length=100, description="과목명")
    professor_name: str = Field(..., min_length=1, max_length=100, description="교수명")
    classroom: str = Field(..., min_length=1, max_length=100, description="강의실")
    day_of_week: DayOfWeekEnum = Field(..., description="요일")
    start_time: time = Field(..., description="시작 시간")
    end_time: time = Field(..., description="종료 시간")

class SubjectCreate(SubjectBase):
    @field_validator('end_time')
    @classmethod
    def validate_time_order(cls, v, info):
        if info.data and 'start_time' in info.data:
            start_time = info.data['start_time']
            if v <= start_time:
                raise ValueError('종료 시간은 시작 시간보다 늦어야 합니다.')
        return v

class SubjectUpdate(BaseModel):
    subject_name: Optional[str] = Field(None, min_length=1, max_length=100)
    professor_name: Optional[str] = Field(None, min_length=1, max_length=100)
    classroom: Optional[str] = Field(None, min_length=1, max_length=100)
    day_of_week: Optional[DayOfWeekEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

class SubjectResponse(SubjectBase):
    subject_id: int
    user_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

# 시간표 관련 스키마
class TimetableBase(BaseModel):
    semester: str = Field(..., min_length=1, max_length=20, description="학기 (예: 2024-1)")
    year: int = Field(..., ge=2020, le=2030, description="년도")
    is_active: bool = Field(True, description="현재 활성 시간표 여부")

class TimetableCreate(TimetableBase):
    pass

class TimetableUpdate(BaseModel):
    semester: Optional[str] = Field(None, min_length=1, max_length=20)
    year: Optional[int] = Field(None, ge=2020, le=2030)
    is_active: Optional[bool] = None

class TimetableResponse(TimetableBase):
    timetable_id: int
    user_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

class TimetableWithSubjects(TimetableResponse):
    subjects: List[SubjectResponse] = Field([], description="시간표에 포함된 과목들")

# 시간표-과목 연결 관련 스키마
class TimetableSubjectCreate(BaseModel):
    subject_id: int = Field(..., description="추가할 과목 ID")

class TimetableSubjectResponse(BaseModel):
    id: int
    timetable_id: int
    subject_id: int
    created_at: datetime
    subject: SubjectResponse
    
    model_config = {"from_attributes": True}

# 시간표 조회용 응답 스키마
class WeeklyTimetableResponse(BaseModel):
    timetable: TimetableResponse
    schedule: dict[str, List[SubjectResponse]] = Field({}, description="요일별 과목 스케줄")
    
    model_config = {"from_attributes": True}

# 채팅 관련 Enums
class RoomTypeEnum(str, Enum):
    DIRECT = "direct"
    GROUP = "group"

class MessageTypeEnum(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    LOCATION = "location"

# 채팅방 관련 스키마
class ChatRoomBase(BaseModel):
    room_name: str = Field(..., min_length=1, max_length=100, description="채팅방 이름")
    room_type: RoomTypeEnum = Field(RoomTypeEnum.DIRECT, description="채팅방 타입")

class ChatRoomCreate(ChatRoomBase):
    participant_ids: Optional[List[int]] = Field([], description="초기 참여자 ID 목록")

class ChatRoomResponse(ChatRoomBase):
    room_id: int
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    participant_count: int = Field(0, description="참여자 수")
    last_message: Optional[str] = Field(None, description="마지막 메시지")
    unread_count: int = Field(0, description="읽지 않은 메시지 수")
    
    model_config = {"from_attributes": True}

# 채팅 참여자 관련 스키마
class ChatParticipantResponse(BaseModel):
    id: int
    room_id: int
    user_id: int
    user_name: str = Field(..., description="참여자 이름")
    joined_at: datetime
    last_read_at: Optional[datetime] = None
    is_active: bool
    
    model_config = {"from_attributes": True}

# 채팅 메시지 관련 스키마
class ChatMessageBase(BaseModel):
    message_content: str = Field(..., min_length=1, max_length=1000, description="메시지 내용")
    message_type: MessageTypeEnum = Field(MessageTypeEnum.TEXT, description="메시지 타입")

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    message_id: int
    room_id: int
    sender_id: int
    sender_name: str = Field(..., description="발신자 이름")
    file_url: Optional[str] = Field(None, description="파일/이미지 URL")
    file_name: Optional[str] = Field(None, description="원본 파일명")
    file_size: Optional[int] = Field(None, description="파일 크기(bytes)")
    reply_to_message_id: Optional[int] = Field(None, description="답장 메시지 ID")
    reply_to_message: Optional[str] = Field(None, description="답장할 메시지 내용")
    is_edited: bool = Field(False, description="수정 여부")
    is_deleted: bool
    edited_at: Optional[datetime] = Field(None, description="수정 시간")
    reactions: List['MessageReactionResponse'] = Field([], description="메시지 반응 목록")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# WebSocket 관련 스키마
class WebSocketMessage(BaseModel):
    type: str = Field(..., description="메시지 타입 (message, join, leave, typing)")
    room_id: int = Field(..., description="채팅방 ID")
    content: Optional[str] = Field(None, description="메시지 내용")
    sender_id: Optional[int] = Field(None, description="발신자 ID")
    sender_name: Optional[str] = Field(None, description="발신자 이름")
    timestamp: Optional[datetime] = Field(None, description="타임스탬프")

# 채팅방 목록 조회용 스키마
class ChatRoomListResponse(BaseModel):
    rooms: List[ChatRoomResponse] = Field([], description="채팅방 목록")
    total_count: int = Field(0, description="전체 채팅방 수")

# 채팅 메시지 목록 조회용 스키마
class ChatMessageListResponse(BaseModel):
    messages: List[ChatMessageResponse] = Field([], description="메시지 목록")
    total_count: int = Field(0, description="전체 메시지 수")
    has_more: bool = Field(False, description="더 많은 메시지 존재 여부")

# 메시지 반응 관련 스키마
class MessageReactionCreate(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=10, description="이모지")

class MessageReactionResponse(BaseModel):
    reaction_id: int
    message_id: int
    user_id: int
    user_name: str = Field(..., description="반응한 사용자 이름")
    emoji: str
    created_at: datetime
    
    model_config = {"from_attributes": True}

# 채팅방 설정 관련 스키마
class FontSizeEnum(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class ChatRoomSettingsUpdate(BaseModel):
    notifications_enabled: Optional[bool] = Field(None, description="알림 활성화")
    notification_sound: Optional[str] = Field(None, description="알림음")
    background_theme: Optional[str] = Field(None, description="배경 테마")
    font_size: Optional[FontSizeEnum] = Field(None, description="글꼴 크기")
    auto_download_images: Optional[bool] = Field(None, description="이미지 자동 다운로드")
    auto_download_files: Optional[bool] = Field(None, description="파일 자동 다운로드")

class ChatRoomSettingsResponse(BaseModel):
    setting_id: int
    room_id: int
    user_id: int
    notifications_enabled: bool
    notification_sound: str
    background_theme: str
    font_size: FontSizeEnum
    auto_download_images: bool
    auto_download_files: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# 예약 메시지 관련 스키마
class ScheduledMessageCreate(BaseModel):
    message_content: str = Field(..., min_length=1, max_length=1000, description="메시지 내용")
    message_type: MessageTypeEnum = Field(MessageTypeEnum.TEXT, description="메시지 타입")
    scheduled_time: datetime = Field(..., description="전송 예정 시간")

class ScheduledMessageResponse(BaseModel):
    scheduled_id: int
    room_id: int
    sender_id: int
    message_content: str
    message_type: MessageTypeEnum
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    scheduled_time: datetime
    is_sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}

# 온라인 상태 관련 스키마
class UserOnlineStatusUpdate(BaseModel):
    status_message: Optional[str] = Field(None, max_length=100, description="상태 메시지")

class UserOnlineStatusResponse(BaseModel):
    user_id: int
    user_name: str = Field(..., description="사용자 이름")
    is_online: bool
    last_seen: datetime
    status_message: Optional[str] = None
    
    model_config = {"from_attributes": True}

# 파일 업로드 관련 스키마
class FileUploadResponse(BaseModel):
    file_url: str = Field(..., description="업로드된 파일 URL")
    file_name: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기(bytes)")
    
# 메시지 검색 관련 스키마
class MessageSearchResponse(BaseModel):
    messages: List[ChatMessageResponse] = Field([], description="검색된 메시지 목록")
    total_count: int = Field(0, description="검색된 메시지 총 개수")
    page: int = Field(1, description="현재 페이지")
    has_more: bool = Field(False, description="더 많은 결과 존재 여부")

# =============================================================================
# 온보딩 관련 스키마
# =============================================================================

# 온보딩 관련 상수 (참고용)
FRIEND_TYPE_EXAMPLES = [
    "학습형", "활동형", "소통형", "취미형",
    "부담없는 동네 친구", "두근두근 썸", "진지한 연애", 
    "편한 동성 친구", "일단 만나보기"
]

STUDENT_STATUS_EXAMPLES = ["재학", "휴학", "졸업", "졸업예정"]

SMOKING_EXAMPLES = ["비흡연", "흡연", "전자담배", "금연중"]

DRINKING_EXAMPLES = ["전혀 안 마심", "피할 수 없을 때만", "가끔 마심", "자주 마심"]

class KeywordTypeEnum(str, Enum):
    PERSONALITY = "personality"
    INTEREST = "interest"
    FRIEND_STYLE = "friend_style"

class MBTIEnum(str, Enum):
    # E/I 조합
    E = "E"  # 외향
    I = "I"  # 내향
    # S/N 조합  
    S = "S"  # 감각
    N = "N"  # 직관
    # T/F 조합
    T = "T"  # 사고
    F = "F"  # 감정
    # P/J 조합
    P = "P"  # 인식
    J = "J"  # 판단

# 온보딩 키워드 옵션들
PERSONALITY_KEYWORDS = [
    "활발한", "차분한", "유머러스한", "진지한", 
    "외향적인", "내향적인", "창의적인", "논리적인"
]

INTEREST_KEYWORDS = [
    "운동", "음악", "영화", "독서", "게임", 
    "요리", "여행", "사진촬영", "공부", "카페"
]

FRIEND_STYLE_KEYWORDS = [
    "함께 공부하는", "운동을 좋아하는", "여행을 즐기는", 
    "음식을 좋아하는", "영화/드라마를 보는", "게임을 하는", 
    "독서를 하는", "음악을 듣는"
]

# 온보딩 프로필 스키마
class UserProfileBase(BaseModel):
    friend_type: str = Field(..., max_length=100, description="친구 유형")
    department: str = Field(..., min_length=1, max_length=100, description="학과")
    student_status: str = Field(..., max_length=50, description="재학 상태")
    smoking: str = Field(..., max_length=50, description="흡연 여부")
    drinking: str = Field(..., max_length=50, description="음주 여부")
    religion: Optional[str] = Field(None, max_length=50, description="종교 (선택사항)")
    mbti: str = Field(..., min_length=4, max_length=4, description="MBTI")

class UserProfileCreate(UserProfileBase):
    personality_keywords: List[str] = Field([], min_items=0, max_items=5, description="성격 키워드 (최대 5개)")
    interest_keywords: List[str] = Field([], min_items=0, max_items=5, description="관심사 키워드 (최대 5개)")
    friend_style_keywords: List[str] = Field([], min_items=0, max_items=5, description="친구 스타일 키워드 (최대 5개)")
    
    @field_validator('mbti')
    @classmethod
    def validate_mbti(cls, v):
        if len(v) != 4:
            raise ValueError('MBTI는 4자리여야 합니다.')
        
        if v[0] not in ['E', 'I']:
            raise ValueError('MBTI 첫 번째 문자는 E 또는 I여야 합니다.')
        if v[1] not in ['S', 'N']:
            raise ValueError('MBTI 두 번째 문자는 S 또는 N이여야 합니다.')
        if v[2] not in ['T', 'F']:
            raise ValueError('MBTI 세 번째 문자는 T 또는 F여야 합니다.')
        if v[3] not in ['P', 'J']:
            raise ValueError('MBTI 네 번째 문자는 P 또는 J여야 합니다.')
        
        return v.upper()
    
    @field_validator('personality_keywords')
    @classmethod
    def validate_personality_keywords(cls, v):
        if len(v) > 5:
            raise ValueError('성격 키워드는 최대 5개까지 선택할 수 있습니다.')
        
        invalid_keywords = [keyword for keyword in v if keyword not in PERSONALITY_KEYWORDS]
        if invalid_keywords:
            raise ValueError(f'유효하지 않은 성격 키워드: {invalid_keywords}')
        
        return v
    
    @field_validator('interest_keywords')
    @classmethod
    def validate_interest_keywords(cls, v):
        if len(v) > 5:
            raise ValueError('관심사 키워드는 최대 5개까지 선택할 수 있습니다.')
        
        invalid_keywords = [keyword for keyword in v if keyword not in INTEREST_KEYWORDS]
        if invalid_keywords:
            raise ValueError(f'유효하지 않은 관심사 키워드: {invalid_keywords}')
        
        return v
    
    @field_validator('friend_style_keywords')
    @classmethod
    def validate_friend_style_keywords(cls, v):
        if len(v) > 5:
            raise ValueError('친구 스타일 키워드는 최대 5개까지 선택할 수 있습니다.')
        
        invalid_keywords = [keyword for keyword in v if keyword not in FRIEND_STYLE_KEYWORDS]
        if invalid_keywords:
            raise ValueError(f'유효하지 않은 친구 스타일 키워드: {invalid_keywords}')
        
        return v

class UserProfileUpdate(BaseModel):
    friend_type: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    student_status: Optional[str] = Field(None, max_length=50)
    smoking: Optional[str] = Field(None, max_length=50)
    drinking: Optional[str] = Field(None, max_length=50)
    religion: Optional[str] = Field(None, max_length=50)
    mbti: Optional[str] = Field(None, min_length=4, max_length=4)
    personality_keywords: Optional[List[str]] = Field(None, max_items=5)
    interest_keywords: Optional[List[str]] = Field(None, max_items=5)
    friend_style_keywords: Optional[List[str]] = Field(None, max_items=5)

class UserKeywordResponse(BaseModel):
    keyword_id: int
    keyword_type: KeywordTypeEnum
    keyword_name: str
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UserImageResponse(BaseModel):
    image_id: int
    image_url: str
    is_primary: bool
    upload_order: int
    file_name: str
    file_size: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UserProfileResponse(UserProfileBase):
    profile_id: int
    user_id: int
    onboarding_completed: bool
    onboarding_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    keywords: List[UserKeywordResponse] = Field([], description="사용자 키워드들")
    images: List[UserImageResponse] = Field([], description="프로필 이미지들")
    
    model_config = {"from_attributes": True}

# 온보딩 진행상황 조회 스키마
class OnboardingProgressResponse(BaseModel):
    user_id: int
    is_completed: bool = Field(False, description="온보딩 완료 여부")
    completed_at: Optional[datetime] = Field(None, description="완료 시각")
    profile_exists: bool = Field(False, description="프로필 정보 존재 여부")
    keywords_count: int = Field(0, description="설정된 키워드 수")
    images_count: int = Field(0, description="업로드된 이미지 수")
    
    model_config = {"from_attributes": True}

# 이미지 업로드 관련 스키마
class ImageUploadResponse(BaseModel):
    message: str
    uploaded_images: List[UserImageResponse]
    total_count: int

# 온보딩 완료 스키마
class OnboardingCompleteRequest(BaseModel):
    pass  # 현재는 추가 데이터 없음

class OnboardingCompleteResponse(BaseModel):
    message: str
    user_id: int
    completed_at: datetime
    profile: UserProfileResponse

# =============================================================================
# 알람 관련 스키마
# =============================================================================

# 알람 타입 Enum
class NotificationTypeEnum(str, Enum):
    CHAT = "chat"
    TIMETABLE = "timetable"
    MATCH = "match"
    SYSTEM = "system"
    REMINDER = "reminder"

# 알람 기본 스키마
class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="알람 제목")
    message: str = Field(..., min_length=1, max_length=1000, description="알람 내용")
    notification_type: NotificationTypeEnum = Field(..., description="알람 타입")
    data: Optional[str] = Field(None, max_length=500, description="추가 데이터 (JSON 형태)")

# 알람 생성 스키마
class NotificationCreate(NotificationBase):
    pass

# 알람 응답 스키마
class NotificationResponse(NotificationBase):
    notification_id: int
    user_id: int
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}

# 알람 목록 조회용 스키마
class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse] = Field([], description="알람 목록")
    total_count: int = Field(0, description="전체 알람 수")
    unread_count: int = Field(0, description="읽지 않은 알람 수")

# 알람 읽음 처리 스키마
class NotificationMarkReadRequest(BaseModel):
    notification_ids: List[int] = Field(..., description="읽음 처리할 알람 ID 목록")

# 알람 통계 스키마
class NotificationStatsResponse(BaseModel):
    total_count: int = Field(0, description="전체 알람 수")
    unread_count: int = Field(0, description="읽지 않은 알람 수")
    by_type: dict[str, int] = Field({}, description="타입별 알람 수")

# =============================================================================
# 그룹/워크스페이스 관련 스키마
# =============================================================================

class GroupBase(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100, description="그룹 이름")
    description: Optional[str] = Field(None, max_length=500, description="그룹 설명")
    is_public: bool = Field(True, description="공개 여부")
    requires_approval: bool = Field(False, description="가입 승인 필요 여부")
    max_members: Optional[int] = Field(None, ge=1, description="최대 멤버 수")

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    group_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    requires_approval: Optional[bool] = None
    max_members: Optional[int] = Field(None, ge=1)

class GroupResponse(GroupBase):
    group_id: int
    created_by: int
    creator_name: str = Field(..., description="생성자 이름")
    is_active: bool
    member_count: int = Field(0, description="멤버 수")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class GroupListResponse(BaseModel):
    groups: List[GroupResponse] = Field([], description="그룹 목록")
    total_count: int = Field(0, description="전체 그룹 수")

class GroupMemberResponse(BaseModel):
    member_id: int
    group_id: int
    user_id: int
    user_name: str = Field(..., description="사용자 이름")
    role: str
    status: str
    joined_at: datetime
    
    model_config = {"from_attributes": True}

class GroupMemberListResponse(BaseModel):
    members: List[GroupMemberResponse] = Field([], description="멤버 목록")
    total_count: int = Field(0, description="전체 멤버 수")

class GroupMemberRoleUpdate(BaseModel):
    role: str = Field(..., description="역할 (owner, admin, member)")

# 게시판 관련 스키마
class GroupPostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="제목")
    content: str = Field(..., min_length=1, max_length=5000, description="내용")

class GroupPostCreate(GroupPostBase):
    pass

class GroupPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=5000)

class GroupPostResponse(GroupPostBase):
    post_id: int
    group_id: int
    author_id: int
    author_name: str = Field(..., description="작성자 이름")
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    comment_count: int = Field(0, description="댓글 수")
    
    model_config = {"from_attributes": True}

class GroupPostListResponse(BaseModel):
    posts: List[GroupPostResponse] = Field([], description="게시글 목록")
    total_count: int = Field(0, description="전체 게시글 수")

class GroupPostCommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="댓글 내용")
    parent_comment_id: Optional[int] = Field(None, description="부모 댓글 ID (대댓글)")

class GroupPostCommentCreate(GroupPostCommentBase):
    pass

class GroupPostCommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=1000)

class GroupPostCommentResponse(GroupPostCommentBase):
    comment_id: int
    post_id: int
    author_id: int
    author_name: str = Field(..., description="작성자 이름")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class GroupPostCommentListResponse(BaseModel):
    comments: List[GroupPostCommentResponse] = Field([], description="댓글 목록")
    total_count: int = Field(0, description="전체 댓글 수")

# 갤러리 관련 스키마
class GroupGalleryResponse(BaseModel):
    image_id: int
    group_id: int
    uploaded_by: int
    uploader_name: str = Field(..., description="업로더 이름")
    image_url: str
    file_name: str
    file_size: int
    description: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}

class GroupGalleryListResponse(BaseModel):
    images: List[GroupGalleryResponse] = Field([], description="이미지 목록")
    total_count: int = Field(0, description="전체 이미지 수")

# 정기모임 관련 스키마
class GroupMeetingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="모임 제목")
    description: Optional[str] = Field(None, max_length=1000, description="모임 설명")
    meeting_date: datetime = Field(..., description="모임 일시")
    location: Optional[str] = Field(None, max_length=200, description="장소")
    max_attendees: Optional[int] = Field(None, ge=1, description="최대 참석자 수")

class GroupMeetingCreate(GroupMeetingBase):
    pass

class GroupMeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    meeting_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    max_attendees: Optional[int] = Field(None, ge=1)

class GroupMeetingResponse(GroupMeetingBase):
    meeting_id: int
    group_id: int
    created_by: int
    creator_name: str = Field(..., description="생성자 이름")
    attendee_count: int = Field(0, description="참석자 수")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class GroupMeetingListResponse(BaseModel):
    meetings: List[GroupMeetingResponse] = Field([], description="모임 목록")
    total_count: int = Field(0, description="전체 모임 수")

class GroupMeetingAttendRequest(BaseModel):
    status: str = Field(..., description="참석 상태 (pending, attending, not_attending)")

# =============================================================================
# 매칭 시스템 관련 스키마
# =============================================================================

class MatchingRecommendationResponse(BaseModel):
    user_id: int
    name: str
    department: Optional[str] = None
    mbti: Optional[str] = None
    profile_images: List[UserImageResponse] = Field([], description="프로필 이미지들")
    common_interests: List[str] = Field([], description="공통 관심사")
    
    model_config = {"from_attributes": True}

class MatchingRecommendationListResponse(BaseModel):
    recommendations: List[MatchingRecommendationResponse] = Field([], description="추천 목록")
    total_count: int = Field(0, description="전체 추천 수")

class MatchingRequestCreate(BaseModel):
    requested_id: int = Field(..., description="요청받은 사용자 ID")

class MatchingRequestResponse(BaseModel):
    request_id: int
    requester_id: int
    requester_name: str = Field(..., description="요청자 이름")
    requested_id: int
    requested_name: str = Field(..., description="요청받은 사람 이름")
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class MatchingRequestListResponse(BaseModel):
    requests: List[MatchingRequestResponse] = Field([], description="요청 목록")
    total_count: int = Field(0, description="전체 요청 수")

class FriendResponse(BaseModel):
    relationship_id: int
    friend_id: int = Field(..., description="친구 사용자 ID")
    friend_name: str = Field(..., description="친구 이름")
    created_at: datetime
    
    model_config = {"from_attributes": True}

class FriendListResponse(BaseModel):
    friends: List[FriendResponse] = Field([], description="친구 목록")
    total_count: int = Field(0, description="전체 친구 수")

# =============================================================================
# 사용자 관리 관련 스키마
# =============================================================================

class UserSearchResponse(BaseModel):
    user_id: int
    name: str
    email: str
    department: Optional[str] = None
    profile_image: Optional[str] = Field(None, description="대표 프로필 이미지")
    
    model_config = {"from_attributes": True}

class UserSearchListResponse(BaseModel):
    users: List[UserSearchResponse] = Field([], description="검색 결과")
    total_count: int = Field(0, description="전체 검색 결과 수")

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, description="새 비밀번호 (최소 8자)")
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        count = sum([has_letter, has_digit, has_special])
        if count < 2:
            raise ValueError('비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 포함해야 합니다.')
        
        return v

class UserBlockResponse(BaseModel):
    block_id: int
    blocked_id: int
    blocked_name: str = Field(..., description="차단된 사용자 이름")
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UserBlockListResponse(BaseModel):
    blocked_users: List[UserBlockResponse] = Field([], description="차단 목록")
    total_count: int = Field(0, description="전체 차단 수")

class UserNotificationSettingsResponse(BaseModel):
    setting_id: int
    user_id: int
    push_enabled: bool
    chat_notifications: bool
    timetable_notifications: bool
    match_notifications: bool
    system_notifications: bool
    reminder_notifications: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class UserNotificationSettingsUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    chat_notifications: Optional[bool] = None
    timetable_notifications: Optional[bool] = None
    match_notifications: Optional[bool] = None
    system_notifications: Optional[bool] = None
    reminder_notifications: Optional[bool] = None