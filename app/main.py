"""
매칭 앱 FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import json
from datetime import datetime
from typing import Dict, List, Optional

# 로컬 모듈 import
from app.models.database import get_db, create_tables
from app.models.models import (
    User, EmailVerification, Subject, Timetable, TimetableSubject,
    ChatRoom, ChatParticipant, ChatMessage, MessageReaction,
    UserProfile, UserImage, UserKeyword, Notification,
    Group, GroupMember, GroupPost, GroupPostComment, GroupGallery, GroupMeeting, GroupMeetingAttendee, GroupLike,
    GroupEvent, GroupEventAttendance, GalleryImageLike, GalleryImageComment, GroupPostLike,
    GroupPostImage, GroupPostCommentLike,
    MatchingRequest, FriendRelationship,
    UserBlock, UserNotificationSettings,
    # 구해요 관련 모델
    RecruitPost, RecruitPostLike, RecruitPostComment, RecruitApplication,
    # 장소 추천 관련 모델
    Place, PlaceImage, PlaceLike, PlaceReview
)
from app.models.schemas import (
    UserCreate, UserResponse, UserLogin, Token, UserMeResponse, UserProfileUpdateRequest, UserProfileUpdate,
    FindUserIdRequest, FindUserIdResponse,
    PasswordResetRequest, VerificationCodeRequest, PasswordResetConfirm,
    # 이메일 인증 관련 스키마
    EmailVerificationRequest, EmailVerificationConfirm, UserCreateWithVerification,
    # 시간표 관련 스키마
    SubjectCreate, SubjectUpdate, SubjectResponse,
    TimetableCreate, TimetableUpdate, TimetableResponse, TimetableWithSubjects,
    TimetableSubjectCreate, WeeklyTimetableResponse,
    # 채팅 관련 스키마
    ChatRoomCreate, ChatRoomResponse, ChatRoomListResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse,
    ChatParticipantResponse, WebSocketMessage, MessageReactionCreate, MessageReactionResponse,
    ChatRoomSettingsUpdate, ChatRoomSettingsResponse, ScheduledMessageCreate, ScheduledMessageResponse,
    UserOnlineStatusUpdate, UserOnlineStatusResponse, FileUploadResponse, MessageSearchResponse,
    # 온보딩 관련 스키마
    UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    OnboardingProgressResponse, ImageUploadResponse, UserImageResponse,
    OnboardingCompleteRequest, OnboardingCompleteResponse,
    KeywordTypeEnum,
    # 알람 관련 스키마
    NotificationCreate, NotificationResponse, NotificationListResponse,
    NotificationMarkReadRequest, NotificationStatsResponse, NotificationTypeEnum,
    # 그룹/워크스페이스 관련 스키마
    GroupCreate, GroupUpdate, GroupResponse, GroupListResponse, GroupLikeResponse, GroupCategoryEnum, GroupCategoryListResponse,
    GroupMemberResponse, GroupMemberListResponse, GroupMemberRoleUpdate,
    # 그룹 통계 관련 스키마
    GroupStatsResponse, MemberGrowthResponse, MemberGrowthData, PostCategoryStatsResponse, PostCategoryStats,
    GroupPostCreate, GroupPostUpdate, GroupPostResponse, GroupPostListResponse,
    GroupPostCommentCreate, GroupPostCommentUpdate, GroupPostCommentResponse, GroupPostCommentListResponse,
    GroupGalleryResponse, GroupGalleryListResponse,
    GroupMeetingCreate, GroupMeetingUpdate, GroupMeetingResponse, GroupMeetingListResponse, GroupMeetingAttendRequest,
    # 그룹 이벤트 관련 스키마
    GroupEventCreate, GroupEventUpdate, GroupEventResponse, GroupEventListResponse,
    GroupEventAttendanceCreate, GroupEventAttendanceResponse,
    # 갤러리 좋아요/댓글 관련 스키마
    GalleryImageLikeResponse, GalleryImageCommentCreate, GalleryImageCommentUpdate,
    GalleryImageCommentResponse, GalleryImageCommentListResponse,
    # 게시글 좋아요 관련 스키마
    GroupPostLikeResponse,
    # 게시글 이미지 & 댓글 좋아요 관련 스키마
    GroupPostImageResponse, GroupPostCommentLikeResponse, GroupPostSearchResponse,
    # 매칭 시스템 관련 스키마
    MatchingRecommendationResponse, MatchingRecommendationListResponse,
    MatchingRequestCreate, MatchingRequestResponse, MatchingRequestListResponse,
    FriendResponse, FriendListResponse,
    # 사용자 관리 관련 스키마
    UserSearchResponse, UserSearchListResponse, PasswordChangeRequest,
    UserBlockResponse, UserBlockListResponse,
    UserNotificationSettingsResponse, UserNotificationSettingsUpdate,
    # 구해요 관련 스키마
    RecruitPostCreate, RecruitPostUpdate, RecruitPostResponse, RecruitPostListResponse,
    RecruitPostLikeResponse, RecruitCommentCreate, RecruitCommentUpdate,
    RecruitCommentResponse, RecruitCommentListResponse,
    RecruitApplicationCreate, RecruitApplicationStatusUpdate,
    RecruitApplicationResponse, RecruitApplicationListResponse,
    MyRecruitApplicationResponse, MyRecruitApplicationListResponse,
    RecruitImageUploadResponse, RecruitAnswerItem,
    # 장소 추천 관련 스키마
    PlaceCreate, PlaceUpdate, PlaceListItemResponse, PlaceListResponse,
    PlaceDetailResponse, PlaceLikeResponse, PlaceImageResponse,
    PlaceReviewCreate, PlaceReviewUpdate, PlaceReviewResponse, PlaceReviewListResponse,
    MyPlaceReviewResponse, MyPlaceReviewListResponse, PlaceImageUploadResponse
)
from app.services.email_service import EmailService
from app.services.image_service import ImageService
from app.auth.security import generate_salt, hash_password_with_salt
from app.auth.jwt_handler import create_access_token
from app.auth.dependencies import authenticate_user, get_current_user

app = FastAPI(
    title="매칭 앱 API",
    description="FastAPI를 사용한 매칭 앱 백엔드 API",
    version="1.0.0",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (이미지 파일들)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 앱 시작 시 테이블 생성
@app.on_event("startup")
async def startup_event():
    try:
        create_tables()
        # create_tables() 내부에서 이미 에러 처리를 하므로 여기서는 성공 메시지만 출력
    except Exception as e:
        # create_tables()에서 처리하지 않은 에러만 여기서 처리
        error_str = str(e)
        if "FOREIGN KEY" not in error_str and "2003" not in error_str:
            import traceback
            traceback.print_exc()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "매칭 앱 API에 오신 것을 환영합니다!"}

# =============================================================================
# 이메일 인증 시스템
# =============================================================================

@app.post("/auth/request-email-verification")
async def request_email_verification(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """회원가입을 위한 이메일 인증번호 발송"""
    try:
        # 이미 가입된 이메일인지 확인
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 이메일입니다."
            )
        
        # 기존 미사용 인증번호가 있다면 삭제
        db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.purpose == "email_verification",
            EmailVerification.is_used == False
        ).delete()
        
        # 새 인증번호 생성
        verification_code = EmailService.generate_verification_code()
        expires_at = EmailService.get_expiry_time()
        
        # 데이터베이스에 인증번호 저장
        verification = EmailVerification(
            email=request.email,
            verification_code=verification_code,
            purpose="email_verification",
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        
        # 이메일 발송
        email_sent = await EmailService.send_verification_email(
            request.email, 
            verification_code, 
            "email_verification"
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
            )
        
        return {
            "message": f"{request.email}로 인증번호가 발송되었습니다. 10분 내에 입력해주세요.",
            "expires_in_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 인증번호 발송 중 오류가 발생했습니다."
        )

@app.post("/auth/verify-email")
async def verify_email(request: EmailVerificationConfirm, db: Session = Depends(get_db)):
    """이메일 인증번호 확인"""
    try:
        # 인증번호 조회
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.purpose == "email_verification",
            EmailVerification.is_used == False
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 인증번호입니다."
            )
        
        # 만료 시간 확인
        if EmailService.is_code_expired(verification.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증번호가 만료되었습니다. 다시 요청해주세요."
            )
        
        return {"message": "이메일 인증이 완료되었습니다. 회원가입을 진행해주세요."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 인증 확인 중 오류가 발생했습니다."
        )

# =============================================================================
# 회원가입 및 로그인
# =============================================================================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreateWithVerification, db: Session = Depends(get_db)):
    """회원가입 (이메일 인증 필요)"""
    try:
        # 이메일 중복 검사
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 이메일입니다."
            )
        
        # 이메일 인증번호 확인
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == user.email,
            EmailVerification.verification_code == user.verification_code,
            EmailVerification.purpose == "email_verification",
            EmailVerification.is_used == False
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 인증번호입니다. 이메일 인증을 먼저 완료해주세요."
            )
        
        # 만료 시간 확인
        if EmailService.is_code_expired(verification.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증번호가 만료되었습니다. 이메일 인증을 다시 요청해주세요."
            )
        
        # 비밀번호 해싱
        salt = generate_salt()
        hashed_password = hash_password_with_salt(user.password, salt)
        
        # 사용자 생성
        db_user = User(
            email=user.email,
            password_hash=hashed_password,
            salt=salt,
            name=user.name,
            birth_date=user.birth_date,
            gender=user.gender.value,
            nationality=user.nationality,
            phone_number=user.phone_number,
            terms_agreed=user.terms_agreed
        )
        
        db.add(db_user)
        
        # 인증번호 사용 처리
        verification.is_used = True
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 정보입니다."
        )
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 중 오류가 발생했습니다: {e}"
        )

@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """로그인"""
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserMeResponse)
async def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """현재 사용자 정보 조회 (확장됨)"""
    try:
        # 사용자 프로필 정보 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()
        
        # 응답 데이터 구성
        response_data = {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "name": current_user.name,
            "birth_date": current_user.birth_date,
            "gender": current_user.gender,
            "nationality": current_user.nationality,
            "phone_number": current_user.phone_number,
            "terms_agreed": current_user.terms_agreed,
            "created_at": current_user.created_at,
            "personality_keywords": [],
            "interest_keywords": [],
            "onboarding_completed": profile.onboarding_completed if profile else False
        }
        
        # 프로필 정보가 있다면 온보딩 정보 추가
        if profile:
            import json
            personality_keywords = json.loads(profile.personality_keywords) if profile.personality_keywords else []
            interest_keywords = json.loads(profile.interest_keywords) if profile.interest_keywords else []
            
            response_data.update({
                "department": profile.department,
                "student_status": profile.student_status,
                "friend_type": profile.friend_type,
                "smoking": profile.smoking,
                "drinking": profile.drinking,
                "mbti": profile.mbti,
                "personality_keywords": personality_keywords,
                "interest_keywords": interest_keywords
            })
        
        return UserMeResponse(**response_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다."
        )

@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """로그아웃"""
    try:
        # JWT 토큰 기반에서는 클라이언트에서 토큰을 삭제하는 것이 일반적
        # 서버에서는 로그아웃 성공 메시지만 반환
        return {
            "message": "성공적으로 로그아웃되었습니다.",
            "user_id": current_user.user_id,
            "email": current_user.email
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 중 오류가 발생했습니다."
        )

@app.get("/users/{user_id}", response_model=UserResponse)
async def read_user(user_id: int, db: Session = Depends(get_db)):
    """특정 사용자 정보 조회"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    return user

# =============================================================================
# 아이디/비밀번호 찾기 시스템
# =============================================================================

@app.post("/auth/find-user-id", response_model=FindUserIdResponse)
async def find_user_id(request: FindUserIdRequest, db: Session = Depends(get_db)):
    """아이디(이메일) 찾기"""
    try:
        # 이름, 생년월일, 연락처로 사용자 조회
        user = db.query(User).filter(
            User.name == request.name,
            User.birth_date == request.birth_date,
            User.phone_number == request.phone_number
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="입력하신 정보와 일치하는 계정을 찾을 수 없습니다."
            )
        
        return FindUserIdResponse(
            email=user.email,
            name=user.name,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="아이디 찾기 중 오류가 발생했습니다."
        )

# 비밀번호 찾기 관련 엔드포인트들
@app.post("/auth/request-password-reset")
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """비밀번호 재설정 인증번호 발송"""
    try:
        # 사용자 존재 확인 (이메일과 이름 모두 일치해야 함)
        user = db.query(User).filter(
            User.email == request.email,
            User.name == request.name
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="입력하신 이메일과 이름이 일치하는 계정을 찾을 수 없습니다."
            )
        
        # 기존 미사용 인증번호가 있다면 삭제
        db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.purpose == "password_reset",
            EmailVerification.is_used == False
        ).delete()
        
        # 새 인증번호 생성
        verification_code = EmailService.generate_verification_code()
        expires_at = EmailService.get_expiry_time()
        
        # 데이터베이스에 인증번호 저장
        verification = EmailVerification(
            email=request.email,
            verification_code=verification_code,
            purpose="password_reset",
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        
        # 이메일 발송
        email_sent = await EmailService.send_verification_email(
            request.email, 
            verification_code, 
            "password_reset"
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
            )
        
        return {
            "message": f"{request.name}님의 이메일({request.email})로 인증번호가 발송되었습니다. 10분 내에 입력해주세요.",
            "expires_in_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 재설정 요청 중 오류가 발생했습니다."
        )

@app.post("/auth/verify-reset-code")
async def verify_reset_code(request: VerificationCodeRequest, db: Session = Depends(get_db)):
    """비밀번호 재설정 인증번호 확인"""
    try:
        # 인증번호 조회
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.purpose == "password_reset",
            EmailVerification.is_used == False
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 인증번호입니다."
            )
        
        # 만료 시간 확인
        if EmailService.is_code_expired(verification.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증번호가 만료되었습니다. 다시 요청해주세요."
            )
        
        return {"message": "인증번호가 확인되었습니다. 새로운 비밀번호를 설정해주세요."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증번호 확인 중 오류가 발생했습니다."
        )

@app.post("/auth/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """비밀번호 재설정"""
    try:
        # 인증번호 확인
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.purpose == "password_reset",
            EmailVerification.is_used == False
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 인증번호입니다."
            )
        
        # 만료 시간 확인
        if EmailService.is_code_expired(verification.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증번호가 만료되었습니다. 다시 요청해주세요."
            )
        
        # 사용자 조회
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 새 비밀번호로 업데이트
        new_salt = generate_salt()
        new_hashed_password = hash_password_with_salt(request.new_password, new_salt)
        
        user.password_hash = new_hashed_password
        user.salt = new_salt
        
        # 인증번호 사용 처리
        verification.is_used = True
        
        db.commit()
        
        return {"message": "비밀번호가 성공적으로 변경되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 재설정 중 오류가 발생했습니다."
        )

# =============================================================================
# 시간표 관련 엔드포인트
# =============================================================================

@app.post("/subjects/", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 과목을 생성합니다."""
    try:
        import json
        
        # 요청 본문을 JSON으로 파싱
        request_body = await request.body()
        request_data = json.loads(request_body.decode('utf-8'))
        
        
        # 수동으로 데이터 검증 및 처리
        subject_data = {
            'subject_name': request_data.get('subject_name', ''),
            'professor_name': request_data.get('professor_name', ''),
            'classroom': request_data.get('classroom', ''),
            'day_of_week': request_data.get('day_of_week', ''),
            'start_time': request_data.get('start_time', ''),
            'end_time': request_data.get('end_time', '')
        }
        
        
        # 시간 형태 변환
        from datetime import time
        
        start_time_str = subject_data['start_time']
        end_time_str = subject_data['end_time']
        
        # "09:00:00" 형태를 time 객체로 변환
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
        
        # 시간 겹침 검사
        existing_subject = db.query(Subject).filter(
            Subject.user_id == current_user.user_id,
            Subject.day_of_week == subject_data['day_of_week'],
            Subject.start_time < end_time,
            Subject.end_time > start_time
        ).first()
        
        if existing_subject:
            error_msg = f"해당 시간대에 이미 등록된 과목이 있습니다: {existing_subject.subject_name}"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 새 과목 생성
        db_subject = Subject(
            user_id=current_user.user_id,
            subject_name=subject_data['subject_name'],
            professor_name=subject_data['professor_name'],
            classroom=subject_data['classroom'],
            day_of_week=subject_data['day_of_week'],
            start_time=start_time,
            end_time=end_time
        )
        
        db.add(db_subject)
        db.commit()
        db.refresh(db_subject)
        
        return db_subject
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="과목 생성 중 오류가 발생했습니다."
        )

@app.get("/subjects/", response_model=list[SubjectResponse])
async def get_subjects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 모든 과목을 조회합니다."""
    try:
        subjects = db.query(Subject).filter(Subject.user_id == current_user.user_id).all()
        return subjects
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"과목 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 과목의 상세 정보를 조회합니다."""
    try:
        subject = db.query(Subject).filter(
            Subject.subject_id == subject_id,
            Subject.user_id == current_user.user_id
        ).first()
        
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="과목을 찾을 수 없습니다."
            )
        
        return subject
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="과목 조회 중 오류가 발생했습니다."
        )

@app.put("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: int,
    subject_update: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """과목 정보를 수정합니다."""
    try:
        subject = db.query(Subject).filter(
            Subject.subject_id == subject_id,
            Subject.user_id == current_user.user_id
        ).first()
        
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="과목을 찾을 수 없습니다."
            )
        
        # 업데이트할 필드들 적용
        update_data = subject_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(subject, field, value)
        
        # 시간 변경 시 겹침 검사
        if 'day_of_week' in update_data or 'start_time' in update_data or 'end_time' in update_data:
            existing_subject = db.query(Subject).filter(
                Subject.user_id == current_user.user_id,
                Subject.subject_id != subject_id,  # 현재 과목 제외
                Subject.day_of_week == subject.day_of_week,
                Subject.start_time < subject.end_time,
                Subject.end_time > subject.start_time
            ).first()
            
            if existing_subject:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"해당 시간대에 이미 등록된 과목이 있습니다: {existing_subject.subject_name}"
                )
        
        db.commit()
        db.refresh(subject)
        
        return subject
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="과목 수정 중 오류가 발생했습니다."
        )

@app.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """과목을 삭제합니다."""
    try:
        subject = db.query(Subject).filter(
            Subject.subject_id == subject_id,
            Subject.user_id == current_user.user_id
        ).first()
        
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="과목을 찾을 수 없습니다."
            )
        
        db.delete(subject)
        db.commit()
        
        return {"message": "과목이 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="과목 삭제 중 오류가 발생했습니다."
        )

@app.post("/timetables/", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED)
async def create_timetable(
    timetable: TimetableCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 시간표를 생성합니다."""
    try:
        # 활성 시간표가 이미 있으면 비활성화
        if timetable.is_active:
            db.query(Timetable).filter(
                Timetable.user_id == current_user.user_id,
                Timetable.is_active == True
            ).update({Timetable.is_active: False})
        
        # 새 시간표 생성
        db_timetable = Timetable(
            user_id=current_user.user_id,
            semester=timetable.semester,
            year=timetable.year,
            is_active=timetable.is_active
        )
        
        db.add(db_timetable)
        db.commit()
        db.refresh(db_timetable)
        
        return db_timetable
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표 생성 중 오류가 발생했습니다."
        )

@app.get("/timetables/", response_model=list[TimetableResponse])
async def get_timetables(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 모든 시간표를 조회합니다."""
    try:
        timetables = db.query(Timetable).filter(
            Timetable.user_id == current_user.user_id
        ).order_by(Timetable.year.desc(), Timetable.semester.desc()).all()
        return timetables
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표 조회 중 오류가 발생했습니다."
        )

@app.get("/timetables/active", response_model=WeeklyTimetableResponse)
async def get_active_timetable(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 활성 시간표를 조회합니다."""
    try:
        # 활성 시간표 조회
        timetable = db.query(Timetable).filter(
            Timetable.user_id == current_user.user_id,
            Timetable.is_active == True
        ).first()
        
        if not timetable:
            # 활성 시간표가 없으면 기본 시간표 생성
            from datetime import datetime
            default_timetable = Timetable(
                user_id=current_user.user_id,
                semester='2024-2',
                year=2024,
                is_active=True,
                created_at=datetime.now()
            )
            
            db.add(default_timetable)
            db.commit()
            db.refresh(default_timetable)
            
            timetable = default_timetable
        
        # 시간표에 연결된 과목들 조회
        timetable_subjects = db.query(TimetableSubject).filter(
            TimetableSubject.timetable_id == timetable.timetable_id
        ).all()
        
        subjects = []
        for ts in timetable_subjects:
            subject = db.query(Subject).filter(Subject.subject_id == ts.subject_id).first()
            if subject:
                subjects.append(subject)
        
        # 요일별로 정리 (SubjectResponse로 변환)
        schedule = {}
        for subject in subjects:
            day = subject.day_of_week
            if day not in schedule:
                schedule[day] = []
            
            # Subject 객체를 SubjectResponse 스키마로 변환
            subject_response = SubjectResponse(
                subject_name=subject.subject_name,
                professor_name=subject.professor_name,
                classroom=subject.classroom,
                day_of_week=subject.day_of_week,
                start_time=subject.start_time,
                end_time=subject.end_time,
                subject_id=subject.subject_id,
                user_id=subject.user_id,
                created_at=subject.created_at
            )
            schedule[day].append(subject_response)
        
        # 각 요일의 과목들을 시간순으로 정렬
        for day in schedule:
            schedule[day].sort(key=lambda x: x.start_time)
        
        return WeeklyTimetableResponse(
            timetable=timetable,
            schedule=schedule
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표 조회 중 오류가 발생했습니다."
        )

@app.post("/timetables/{timetable_id}/subjects/")
async def add_subject_to_timetable(
    timetable_id: int,
    subject_data: TimetableSubjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ):
    """시간표에 과목을 추가합니다."""
    try:
        # 시간표 소유권 확인
        timetable = db.query(Timetable).filter(
            Timetable.timetable_id == timetable_id,
            Timetable.user_id == current_user.user_id
        ).first()
        
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시간표를 찾을 수 없습니다."
            )
        
        # 과목 소유권 확인
        subject = db.query(Subject).filter(
            Subject.subject_id == subject_data.subject_id,
            Subject.user_id == current_user.user_id
        ).first()
        
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="과목을 찾을 수 없습니다."
            )
        
        # 이미 추가된 과목인지 확인
        existing = db.query(TimetableSubject).filter(
            TimetableSubject.timetable_id == timetable_id,
            TimetableSubject.subject_id == subject_data.subject_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="해당 과목이 이미 시간표에 추가되어 있습니다."
            )
        
        # 시간표에 과목 추가
        timetable_subject = TimetableSubject(
            timetable_id=timetable_id,
            subject_id=subject_data.subject_id
        )
        
        db.add(timetable_subject)
        db.commit()
        
        return {"message": f"'{subject.subject_name}' 과목이 시간표에 추가되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표에 과목 추가 중 오류가 발생했습니다."
        )

@app.delete("/timetables/{timetable_id}/subjects/{subject_id}")
async def remove_subject_from_timetable(
    timetable_id: int,
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시간표에서 과목을 제거합니다."""
    try:
        # 시간표 소유권 확인
        timetable = db.query(Timetable).filter(
            Timetable.timetable_id == timetable_id,
            Timetable.user_id == current_user.user_id
        ).first()
        
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시간표를 찾을 수 없습니다."
            )
        
        # 시간표-과목 연결 찾기
        timetable_subject = db.query(TimetableSubject).filter(
            TimetableSubject.timetable_id == timetable_id,
            TimetableSubject.subject_id == subject_id
        ).first()
        
        if not timetable_subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시간표에서 해당 과목을 찾을 수 없습니다."
            )
        
        db.delete(timetable_subject)
        db.commit()
        
        return {"message": "과목이 시간표에서 제거되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표에서 과목 제거 중 오류가 발생했습니다."
        )

# =============================================================================
# 채팅 시스템
# =============================================================================

# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        # 활성 연결: {room_id: {user_id: websocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: int, user_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket
    
    def disconnect(self, room_id: int, user_id: int):
        if room_id in self.active_connections:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]
                
                # 방에 아무도 없으면 방 정보 삭제
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
    
    async def send_personal_message(self, message: str, room_id: int, user_id: int):
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            await self.active_connections[room_id][user_id].send_text(message)
    
    async def broadcast_to_room(self, message: str, room_id: int, exclude_user: int = None):
        
        if room_id in self.active_connections:
            for user_id, websocket in self.active_connections[room_id].items():
                if exclude_user is None or user_id != exclude_user:
                    try:
                        await websocket.send_text(message)
                    except Exception:
                        pass

# 전역 연결 관리자
manager = ConnectionManager()

# WebSocket 엔드포인트
@app.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    user = None  # user 변수 초기화
    try:
        # JWT 토큰으로 사용자 인증
        from app.auth.jwt_handler import verify_token_string
        from app.auth.dependencies import get_user_by_email
        
        token_data = verify_token_string(token)
        if not token_data or not token_data.email:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user = get_user_by_email(db, token_data.email)
        if not user:
            await websocket.close(code=4002, reason="User not found")
            return
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            await websocket.close(code=4003, reason="Not authorized for this room")
            return
        
        # WebSocket 연결
        await manager.connect(websocket, room_id, user.user_id)
        
        # 입장 알림
        join_message = {
            "type": "join",
            "room_id": room_id,
            "sender_id": user.user_id,
            "sender_name": user.name,
            "content": f"{user.name}님이 입장하셨습니다.",
            "timestamp": datetime.now().isoformat()
        }
        try:
            await manager.broadcast_to_room(json.dumps(join_message), room_id, user.user_id)
        except Exception:
            pass
        
        while True:
            try:
                # 메시지 수신 (타임아웃 없이 대기)
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "잘못된 메시지 형식입니다."
                    }))
                    continue
                
                if message_data.get("type") == "heartbeat":
                    # 하트비트 응답
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_response",
                        "timestamp": datetime.now().isoformat()
                    }))
                    continue
                
                elif message_data.get("type") == "message":
                    
                    # 메시지를 데이터베이스에 저장
                    try:
                        new_message = ChatMessage(
                            room_id=room_id,
                            sender_id=user.user_id,
                            message_content=message_data.get("content", ""),
                            message_type=message_data.get("message_type", "text"),
                            file_url=message_data.get("file_url"),
                            file_name=message_data.get("file_name"),
                            file_size=message_data.get("file_size"),
                            reply_to_message_id=message_data.get("reply_to_message_id")
                        )
                        db.add(new_message)
                        db.commit()
                        db.refresh(new_message)
                    except Exception as db_error:
                        db.rollback()
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "메시지 저장에 실패했습니다."
                        }))
                        continue
                
                # 답장 메시지 정보 가져오기
                reply_to_message = None
                if new_message.reply_to_message_id:
                    reply_msg = db.query(ChatMessage).filter(
                        ChatMessage.message_id == new_message.reply_to_message_id
                    ).first()
                    if reply_msg:
                        reply_sender = db.query(User).filter(User.user_id == reply_msg.sender_id).first()
                        reply_to_message = {
                            "message_id": reply_msg.message_id,
                            "content": reply_msg.message_content[:100],
                            "sender_name": reply_sender.name if reply_sender else "Unknown"
                        }
                
                    # 실시간 브로드캐스트
                    try:
                        broadcast_message = {
                            "type": "message",
                            "message_id": new_message.message_id,
                            "room_id": room_id,
                            "sender_id": user.user_id,
                            "sender_name": user.name,
                            "content": new_message.message_content,
                            "message_type": new_message.message_type,
                            "file_url": new_message.file_url,
                            "file_name": new_message.file_name,
                            "file_size": new_message.file_size,
                            "reply_to_message": reply_to_message,
                            "timestamp": new_message.created_at.isoformat()
                        }
                        await manager.broadcast_to_room(json.dumps(broadcast_message), room_id)
                    except Exception:
                        pass
                
                elif message_data.get("type") == "typing":
                    # 타이핑 상태 브로드캐스트
                    try:
                        typing_message = {
                            "type": "typing",
                            "room_id": room_id,
                            "sender_id": user.user_id,
                            "sender_name": user.name,
                            "timestamp": datetime.now().isoformat()
                        }
                        await manager.broadcast_to_room(json.dumps(typing_message), room_id, user.user_id)
                    except Exception:
                        pass
                        
            except WebSocketDisconnect:
                break
            except Exception as message_error:
                import traceback
                traceback.print_exc()
                # RuntimeError가 발생하면 연결이 끊어진 것이므로 루프 종료
                if "Cannot call \"receive\" once a disconnect message has been received" in str(message_error):
                    break
                # 다른 에러는 계속 진행
                
    except WebSocketDisconnect:
        if user:  # user가 정의된 경우에만 실행
            manager.disconnect(room_id, user.user_id)
            # 퇴장 알림
            leave_message = {
                "type": "leave",
                "room_id": room_id,
                "sender_id": user.user_id,
                "sender_name": user.name,
                "content": f"{user.name}님이 퇴장하셨습니다.",
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast_to_room(json.dumps(leave_message), room_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        if user:  # user가 정의된 경우에만 실행
            manager.disconnect(room_id, user.user_id)

# =============================================================================
# 채팅 REST API 엔드포인트
# =============================================================================

@app.post("/chat/rooms/", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 채팅방을 생성합니다."""
    try:
        # 새 채팅방 생성
        new_room = ChatRoom(
            room_name=room_data.room_name,
            room_type=room_data.room_type,
            created_by=current_user.user_id
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        
        # 생성자를 참여자로 추가
        creator_participant = ChatParticipant(
            room_id=new_room.room_id,
            user_id=current_user.user_id
        )
        db.add(creator_participant)
        
        # 초기 참여자들 추가
        for participant_id in room_data.participant_ids:
            if participant_id != current_user.user_id:  # 생성자 중복 방지
                participant = ChatParticipant(
                    room_id=new_room.room_id,
                    user_id=participant_id
                )
                db.add(participant)
        
        db.commit()
        
        return ChatRoomResponse(
            room_id=new_room.room_id,
            room_name=new_room.room_name,
            room_type=new_room.room_type,
            created_by=new_room.created_by,
            is_active=new_room.is_active,
            created_at=new_room.created_at,
            updated_at=new_room.updated_at,
            participant_count=len(room_data.participant_ids) + 1
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 생성 중 오류가 발생했습니다."
        )

@app.get("/chat/rooms/", response_model=ChatRoomListResponse)
async def get_chat_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자가 참여 중인 채팅방 목록을 조회합니다."""
    try:
        # 사용자가 참여 중인 채팅방들 조회
        user_rooms = db.query(ChatRoom).join(ChatParticipant).filter(
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True,
            ChatRoom.is_active == True
        ).order_by(ChatRoom.updated_at.desc()).all()
        
        rooms_response = []
        for room in user_rooms:
            # 참여자 수 계산
            participant_count = db.query(ChatParticipant).filter(
                ChatParticipant.room_id == room.room_id,
                ChatParticipant.is_active == True
            ).count()
            
            # 마지막 메시지 조회
            last_message = db.query(ChatMessage).filter(
                ChatMessage.room_id == room.room_id,
                ChatMessage.is_deleted == False
            ).order_by(ChatMessage.created_at.desc()).first()
            
            # 읽지 않은 메시지 수 계산
            user_participant = db.query(ChatParticipant).filter(
                ChatParticipant.room_id == room.room_id,
                ChatParticipant.user_id == current_user.user_id
            ).first()
            
            unread_count = 0
            if user_participant and user_participant.last_read_at:
                unread_count = db.query(ChatMessage).filter(
                    ChatMessage.room_id == room.room_id,
                    ChatMessage.created_at > user_participant.last_read_at,
                    ChatMessage.is_deleted == False
                ).count()
            else:
                unread_count = db.query(ChatMessage).filter(
                    ChatMessage.room_id == room.room_id,
                    ChatMessage.is_deleted == False
                ).count()
            
            # 1:1 채팅일 경우 상대방 정보 조회
            other_user_id = None
            other_user_name = None
            other_user_profile_image = None
            
            if room.room_type == 'direct':
                # 나를 제외한 상대방 찾기
                other_participant = db.query(ChatParticipant).join(User).filter(
                    ChatParticipant.room_id == room.room_id,
                    ChatParticipant.user_id != current_user.user_id,
                    ChatParticipant.is_active == True
                ).first()
                
                if other_participant:
                    other_user = db.query(User).filter(User.user_id == other_participant.user_id).first()
                    if other_user:
                        other_user_id = other_user.user_id
                        other_user_name = other_user.name
                        other_user_profile_image = other_user.profile_image
            
            room_response = ChatRoomResponse(
                room_id=room.room_id,
                room_name=room.room_name,
                room_type=room.room_type,
                created_by=room.created_by,
                is_active=room.is_active,
                created_at=room.created_at,
                updated_at=room.updated_at,
                participant_count=participant_count,
                last_message=last_message.message_content if last_message else None,
                unread_count=unread_count,
                other_user_id=other_user_id,
                other_user_name=other_user_name,
                other_user_profile_image=other_user_profile_image
            )
            rooms_response.append(room_response)
        
        return ChatRoomListResponse(
            rooms=rooms_response,
            total_count=len(rooms_response)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/chat/rooms/{room_id}/messages/", response_model=ChatMessageListResponse)
async def get_chat_messages(
    room_id: int,
    page: int = 1,
    size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방의 메시지 목록을 조회합니다."""
    try:
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 메시지 조회 (페이지네이션)
        offset = (page - 1) * size
        messages_query = db.query(ChatMessage).filter(
            ChatMessage.room_id == room_id,
            ChatMessage.is_deleted == False
        ).order_by(ChatMessage.created_at.desc())
        
        total_count = messages_query.count()
        messages = messages_query.offset(offset).limit(size).all()
        
        # 메시지 응답 생성
        messages_response = []
        for message in reversed(messages):  # 시간 순으로 정렬
            sender = db.query(User).filter(User.user_id == message.sender_id).first()
            
            # 답장 메시지 정보 가져오기
            reply_to_message = None
            if message.reply_to_message_id:
                reply_msg = db.query(ChatMessage).filter(
                    ChatMessage.message_id == message.reply_to_message_id
                ).first()
                reply_to_message = reply_msg.message_content[:100] if reply_msg else None
            
            # 반응 정보 가져오기
            reactions = db.query(MessageReaction).filter(
                MessageReaction.message_id == message.message_id
            ).all()
            
            reactions_response = []
            for reaction in reactions:
                reaction_user = db.query(User).filter(User.user_id == reaction.user_id).first()
                reactions_response.append(MessageReactionResponse(
                    reaction_id=reaction.reaction_id,
                    message_id=reaction.message_id,
                    user_id=reaction.user_id,
                    user_name=reaction_user.name if reaction_user else "Unknown",
                    emoji=reaction.emoji,
                    created_at=reaction.created_at
                ))
            
            message_response = ChatMessageResponse(
                message_id=message.message_id,
                room_id=message.room_id,
                sender_id=message.sender_id,
                sender_name=sender.name if sender else "Unknown",
                message_content=message.message_content,
                message_type=message.message_type,
                file_url=message.file_url,
                file_name=message.file_name,
                file_size=message.file_size,
                reply_to_message_id=message.reply_to_message_id,
                reply_to_message=reply_to_message,
                is_edited=message.is_edited,
                is_deleted=message.is_deleted,
                edited_at=message.edited_at,
                reactions=reactions_response,
                created_at=message.created_at,
                updated_at=message.updated_at
            )
            messages_response.append(message_response)
        
        # 읽음 상태 업데이트
        participant.last_read_at = datetime.now()
        db.commit()
        
        return ChatMessageListResponse(
            messages=messages_response,
            total_count=total_count,
            has_more=total_count > page * size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅 메시지 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 온보딩 시스템 API
# =============================================================================

@app.get("/api/users/{user_id}/onboarding/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """온보딩 진행상황 조회"""
    try:
        # 본인만 조회 가능
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 온보딩 정보만 조회할 수 있습니다."
            )
        
        # 프로필 정보 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        # 키워드 수 조회
        keywords_count = db.query(UserKeyword).filter(UserKeyword.user_id == user_id).count()
        
        # 이미지 수 조회
        images_count = db.query(UserImage).filter(UserImage.user_id == user_id).count()
        
        return OnboardingProgressResponse(
            user_id=user_id,
            is_completed=profile.onboarding_completed if profile else False,
            completed_at=profile.onboarding_completed_at if profile else None,
            profile_exists=profile is not None,
            keywords_count=keywords_count,
            images_count=images_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온보딩 진행상황 조회 중 오류가 발생했습니다."
        )

@app.put("/api/users/{user_id}/onboarding", response_model=UserProfileResponse)
async def save_onboarding_data(
    user_id: int,
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """온보딩 데이터 저장"""
    try:
        # 본인만 수정 가능
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 온보딩 정보만 수정할 수 있습니다."
            )
        
        # 기존 프로필 조회
        existing_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if existing_profile:
            # 기존 프로필 업데이트
            for field, value in profile_data.model_dump(exclude={'personality_keywords', 'interest_keywords', 'friend_style_keywords'}).items():
                setattr(existing_profile, field, value)
            existing_profile.updated_at = datetime.now()
            profile = existing_profile
        else:
            # 새 프로필 생성
            profile = UserProfile(
                user_id=user_id,
                **profile_data.model_dump(exclude={'personality_keywords', 'interest_keywords', 'friend_style_keywords'})
            )
            db.add(profile)
        
        # 기존 키워드들 삭제
        db.query(UserKeyword).filter(UserKeyword.user_id == user_id).delete()
        
        # 새 키워드들 추가
        all_keywords = []
        
        # 성격 키워드
        for keyword in profile_data.personality_keywords:
            all_keywords.append(UserKeyword(
                user_id=user_id,
                keyword_type='personality',
                keyword_name=keyword
            ))
        
        # 관심사 키워드
        for keyword in profile_data.interest_keywords:
            all_keywords.append(UserKeyword(
                user_id=user_id,
                keyword_type='interest',
                keyword_name=keyword
            ))
        
        # 친구 스타일 키워드
        for keyword in profile_data.friend_style_keywords:
            all_keywords.append(UserKeyword(
                user_id=user_id,
                keyword_type='friend_style',
                keyword_name=keyword
            ))
        
        # 키워드들 추가
        if all_keywords:
            db.add_all(all_keywords)
        
        db.commit()
        db.refresh(profile)
        
        # 키워드와 이미지 정보 포함하여 응답 생성
        keywords = db.query(UserKeyword).filter(UserKeyword.user_id == user_id).all()
        images = db.query(UserImage).filter(UserImage.user_id == user_id).all()
        
        # UserProfileResponse로 변환
        response_data = profile.__dict__.copy()
        response_data['keywords'] = keywords
        response_data['images'] = images
        
        return UserProfileResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온보딩 데이터 저장 중 오류가 발생했습니다."
        )

@app.post("/api/users/{user_id}/images", response_model=ImageUploadResponse)
async def upload_profile_images(
    user_id: int,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로필 이미지 업로드"""
    try:
        # 본인만 업로드 가능
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 이미지만 업로드할 수 있습니다."
            )
        
        # 기존 이미지 개수 확인
        existing_count = db.query(UserImage).filter(UserImage.user_id == user_id).count()
        
        if existing_count + len(images) > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"최대 6개의 이미지만 업로드할 수 있습니다. (현재: {existing_count}개)"
            )
        
        # 이미지 저장
        saved_images = await ImageService.save_multiple_images(images, user_id)
        
        # 데이터베이스에 이미지 정보 저장
        db_images = []
        for i, (file_path, original_filename, file_size) in enumerate(saved_images):
            order = existing_count + i + 1
            is_primary = existing_count == 0 and i == 0  # 첫 번째 이미지가 대표 이미지
            
            db_image = UserImage(
                user_id=user_id,
                image_url=file_path,
                is_primary=is_primary,
                upload_order=order,
                file_name=original_filename,
                file_size=file_size
            )
            db.add(db_image)
            db_images.append(db_image)
        
        db.commit()
        
        # 응답 생성
        for db_image in db_images:
            db.refresh(db_image)
        
        return ImageUploadResponse(
            message=f"{len(saved_images)}개의 이미지가 성공적으로 업로드되었습니다.",
            uploaded_images=db_images,
            total_count=existing_count + len(saved_images)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 업로드 중 오류가 발생했습니다."
        )

@app.delete("/api/users/{user_id}/images/{image_id}")
async def delete_profile_image(
    user_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로필 이미지 삭제"""
    try:
        # 본인만 삭제 가능
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 이미지만 삭제할 수 있습니다."
            )
        
        # 이미지 조회
        image = db.query(UserImage).filter(
            UserImage.image_id == image_id,
            UserImage.user_id == user_id
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 파일 삭제
        await ImageService.delete_image(image.image_url)
        
        # 데이터베이스에서 삭제
        db.delete(image)
        
        # 대표 이미지였다면 다른 이미지를 대표로 설정
        if image.is_primary:
            next_image = db.query(UserImage).filter(
                UserImage.user_id == user_id,
                UserImage.image_id != image_id
            ).order_by(UserImage.upload_order).first()
            
            if next_image:
                next_image.is_primary = True
        
        db.commit()
        
        return {"message": "이미지가 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 삭제 중 오류가 발생했습니다."
        )

@app.put("/api/users/{user_id}/images/{image_id}/primary")
async def set_primary_image(
    user_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로필 대표 이미지 설정"""
    try:
        # 권한 확인 (본인만 가능)
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 프로필 이미지만 변경할 수 있습니다."
            )
        
        # 선택한 이미지 조회
        selected_image = db.query(UserImage).filter(
            UserImage.image_id == image_id,
            UserImage.user_id == user_id
        ).first()
        
        if not selected_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 이미 대표 이미지인 경우
        if selected_image.is_primary:
            return {
                "message": "이미 대표 이미지로 설정되어 있습니다.",
                "image": {
                    "image_id": selected_image.image_id,
                    "image_url": selected_image.image_url,
                    "is_primary": selected_image.is_primary
                }
            }
        
        # 기존 대표 이미지의 is_primary를 False로 변경
        current_primary = db.query(UserImage).filter(
            UserImage.user_id == user_id,
            UserImage.is_primary == True
        ).first()
        
        if current_primary:
            current_primary.is_primary = False
        
        # 선택한 이미지를 대표 이미지로 설정
        selected_image.is_primary = True
        
        db.commit()
        db.refresh(selected_image)
        
        return {
            "message": "대표 이미지가 변경되었습니다.",
            "image": {
                "image_id": selected_image.image_id,
                "image_url": selected_image.image_url,
                "is_primary": selected_image.is_primary,
                "upload_order": selected_image.upload_order
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대표 이미지 설정 중 오류가 발생했습니다."
        )

@app.post("/api/users/{user_id}/onboarding/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """온보딩 완료 처리"""
    try:
        # 본인만 완료 처리 가능
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 온보딩만 완료할 수 있습니다."
            )
        
        # 프로필 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="온보딩 프로필 정보가 없습니다. 먼저 프로필을 설정해주세요."
            )
        
        # 필수 정보 확인
        keywords_count = db.query(UserKeyword).filter(UserKeyword.user_id == user_id).count()
        images_count = db.query(UserImage).filter(UserImage.user_id == user_id).count()
        
        if keywords_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="키워드를 하나 이상 설정해주세요."
            )
        
        if images_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="프로필 이미지를 하나 이상 업로드해주세요."
            )
        
        # 온보딩 완료 처리
        profile.onboarding_completed = True
        profile.onboarding_completed_at = datetime.now()
        profile.updated_at = datetime.now()
        
        db.commit()
        db.refresh(profile)
        
        # 응답 생성 (키워드와 이미지 포함)
        keywords = db.query(UserKeyword).filter(UserKeyword.user_id == user_id).all()
        images = db.query(UserImage).filter(UserImage.user_id == user_id).all()
        
        response_data = profile.__dict__.copy()
        response_data['keywords'] = keywords
        response_data['images'] = images
        
        return OnboardingCompleteResponse(
            message="온보딩이 성공적으로 완료되었습니다!",
            user_id=user_id,
            completed_at=profile.onboarding_completed_at,
            profile=UserProfileResponse(**response_data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온보딩 완료 처리 중 오류가 발생했습니다."
        )

@app.get("/api/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 조회"""
    try:
        # 프로필 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필을 찾을 수 없습니다."
            )
        
        # 이미지 정보 조회
        images = db.query(UserImage).filter(UserImage.user_id == user_id).order_by(UserImage.upload_order).all()
        
        # 명시적으로 응답 생성 (SQLAlchemy 내부 속성 제외)
        # keywords는 JSON으로 저장되어 있으므로 빈 배열 반환
        return UserProfileResponse(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            friend_type=profile.friend_type,
            department=profile.department,
            student_status=profile.student_status,
            smoking=profile.smoking,
            drinking=profile.drinking,
            religion=profile.religion,
            mbti=profile.mbti,
            personality_keywords=profile.personality_keywords,
            interest_keywords=profile.interest_keywords,
            friend_style_keywords=profile.friend_style_keywords,
            onboarding_completed=profile.onboarding_completed,
            onboarding_completed_at=profile.onboarding_completed_at,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            keywords=[],  # 키워드는 JSON으로 저장되어 있음 (personality_keywords, interest_keywords, friend_style_keywords)
            images=[UserImageResponse(
                image_id=img.image_id,
                image_url=img.image_url,
                is_primary=img.is_primary,
                upload_order=img.upload_order,
                file_name=img.file_name,
                file_size=img.file_size,
                created_at=img.created_at
            ) for img in images]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 개인정보 수정 API
# =============================================================================

@app.put("/api/users/profile")
async def update_user_profile(
    profile_update: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 개인정보 수정 (이름)"""
    try:
        # 수정할 필드가 있는지 확인
        if profile_update.name is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 이름을 입력해주세요."
            )
        
        # 사용자 이름 업데이트
        db.query(User).filter(User.user_id == current_user.user_id).update({"name": profile_update.name})
        db.commit()
        
        # 업데이트된 사용자 정보 조회
        updated_user = db.query(User).filter(User.user_id == current_user.user_id).first()
        
        return {
            "message": "이름이 성공적으로 수정되었습니다.",
            "updated_fields": ["name"],
            "user": {
                "user_id": updated_user.user_id,
                "name": updated_user.name,
                "email": updated_user.email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="개인정보 수정 중 오류가 발생했습니다."
        )

# =============================================================================
# 온보딩 프로필 수정 API
# =============================================================================

@app.get("/api/users/onboarding/profile")
async def get_onboarding_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """온보딩 프로필 정보 조회"""
    try:
        import json
        
        # 프로필 정보 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()
        
        if not profile:
            return {
                "message": "온보딩 프로필이 없습니다.",
                "profile": None
            }
        
        return {
            "message": "온보딩 프로필 조회 성공",
            "profile": {
                "friend_type": profile.friend_type,
                "department": profile.department,
                "student_status": profile.student_status,
                "smoking": profile.smoking,
                "drinking": profile.drinking,
                "religion": profile.religion,
                "mbti": profile.mbti,
                "personality_keywords": json.loads(profile.personality_keywords) if profile.personality_keywords else [],
                "interest_keywords": json.loads(profile.interest_keywords) if profile.interest_keywords else [],
                "friend_style_keywords": json.loads(profile.friend_style_keywords) if profile.friend_style_keywords else [],
                "onboarding_completed": profile.onboarding_completed
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온보딩 프로필 조회 중 오류가 발생했습니다."
        )

@app.get("/api/users/{user_id}/onboarding/profile")
async def get_user_onboarding_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 사용자의 온보딩 프로필 정보 조회 (본인만 가능)"""
    try:
        import json
        
        # 본인만 조회 가능
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 온보딩 정보만 조회할 수 있습니다."
            )
        
        # 프로필 정보 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            return {
                "message": "온보딩 프로필이 없습니다.",
                "profile": None
            }
        
        return {
            "message": "온보딩 프로필 조회 성공",
            "profile": {
                "friend_type": profile.friend_type,
                "department": profile.department,
                "student_status": profile.student_status,
                "smoking": profile.smoking,
                "drinking": profile.drinking,
                "religion": profile.religion,
                "mbti": profile.mbti,
                "personality_keywords": json.loads(profile.personality_keywords) if profile.personality_keywords else [],
                "interest_keywords": json.loads(profile.interest_keywords) if profile.interest_keywords else [],
                "friend_style_keywords": json.loads(profile.friend_style_keywords) if profile.friend_style_keywords else [],
                "onboarding_completed": profile.onboarding_completed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온보딩 프로필 조회 중 오류가 발생했습니다."
        )

@app.put("/api/users/onboarding/profile")
async def update_onboarding_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """온보딩 프로필 정보 저장/수정"""
    try:
        import json
        
        # 요청 본문을 JSON으로 파싱
        request_body = await request.body()
        request_data = json.loads(request_body.decode('utf-8'))
        
        
        # 수동으로 데이터 검증 및 처리
        profile_data = {
            'friend_type': request_data.get('friend_type', ''),
            'department': request_data.get('department', ''),
            'student_status': request_data.get('student_status', ''),
            'smoking': request_data.get('smoking', ''),
            'drinking': request_data.get('drinking', ''),
            'religion': request_data.get('religion', ''),
            'mbti': request_data.get('mbti', ''),
            'personality_keywords': request_data.get('personality_keywords', []),
            'interest_keywords': request_data.get('interest_keywords', []),
            'friend_style_keywords': request_data.get('friend_style_keywords', [])
        }
        
        
        # 기존 프로필 조회
        existing_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()
        
        if existing_profile:
            # 기존 프로필 업데이트
            existing_profile.friend_type = profile_data['friend_type']
            existing_profile.department = profile_data['department']
            existing_profile.student_status = profile_data['student_status']
            existing_profile.smoking = profile_data['smoking']
            existing_profile.drinking = profile_data['drinking']
            existing_profile.religion = profile_data['religion']
            existing_profile.mbti = profile_data['mbti']
            
            # 키워드들을 JSON으로 저장
            existing_profile.personality_keywords = json.dumps(profile_data['personality_keywords'], ensure_ascii=False) if profile_data['personality_keywords'] else None
            existing_profile.interest_keywords = json.dumps(profile_data['interest_keywords'], ensure_ascii=False) if profile_data['interest_keywords'] else None
            existing_profile.friend_style_keywords = json.dumps(profile_data['friend_style_keywords'], ensure_ascii=False) if profile_data['friend_style_keywords'] else None
            
            existing_profile.updated_at = datetime.now()
            profile = existing_profile
        else:
            # 새 프로필 생성
            profile = UserProfile(
                user_id=current_user.user_id,
                friend_type=profile_data['friend_type'],
                department=profile_data['department'],
                student_status=profile_data['student_status'],
                smoking=profile_data['smoking'],
                drinking=profile_data['drinking'],
                religion=profile_data['religion'],
                mbti=profile_data['mbti'],
                personality_keywords=json.dumps(profile_data['personality_keywords'], ensure_ascii=False) if profile_data['personality_keywords'] else None,
                interest_keywords=json.dumps(profile_data['interest_keywords'], ensure_ascii=False) if profile_data['interest_keywords'] else None,
                friend_style_keywords=json.dumps(profile_data['friend_style_keywords'], ensure_ascii=False) if profile_data['friend_style_keywords'] else None,
                onboarding_completed=False,
                created_at=datetime.now()
            )
            db.add(profile)
        
        db.commit()
        db.refresh(profile)
        
        return {
            "message": "온보딩 프로필이 성공적으로 저장되었습니다.",
            "profile": {
                "friend_type": profile.friend_type,
                "department": profile.department,
                "student_status": profile.student_status,
                "smoking": profile.smoking,
                "drinking": profile.drinking,
                "religion": profile.religion,
                "mbti": profile.mbti,
                "personality_keywords": json.loads(profile.personality_keywords) if profile.personality_keywords else [],
                "interest_keywords": json.loads(profile.interest_keywords) if profile.interest_keywords else [],
                "friend_style_keywords": json.loads(profile.friend_style_keywords) if profile.friend_style_keywords else []
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 수정 중 오류가 발생했습니다."
        )

@app.put("/api/users/onboarding/profile")
async def update_onboarding_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """온보딩 프로필 정보 저장 (프론트엔드 요청에 맞춤)"""
    try:
        # 기존 프로필 조회
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()
        
        if profile:
            # 기존 프로필 업데이트
            profile.friend_type = profile_data.friend_type
            profile.department = profile_data.department
            profile.student_status = profile_data.student_status
            profile.smoking = profile_data.smoking
            profile.drinking = profile_data.drinking
            profile.mbti = profile_data.mbti
            profile.religion = profile_data.religion
            
            # 키워드를 JSON으로 저장
            import json
            profile.personality_keywords = json.dumps(profile_data.personality_keywords, ensure_ascii=False)
            profile.interest_keywords = json.dumps(profile_data.interest_keywords, ensure_ascii=False)
            profile.friend_style_keywords = json.dumps(profile_data.friend_style_keywords, ensure_ascii=False)
            
            profile.updated_at = datetime.now()
        else:
            # 새 프로필 생성
            import json
            profile = UserProfile(
                user_id=current_user.user_id,
                friend_type=profile_data.friend_type,
                department=profile_data.department,
                student_status=profile_data.student_status,
                smoking=profile_data.smoking,
                drinking=profile_data.drinking,
                religion=profile_data.religion,
                mbti=profile_data.mbti,
                personality_keywords=json.dumps(profile_data.personality_keywords, ensure_ascii=False),
                interest_keywords=json.dumps(profile_data.interest_keywords, ensure_ascii=False),
                friend_style_keywords=json.dumps(profile_data.friend_style_keywords, ensure_ascii=False),
                onboarding_completed=False,
                created_at=datetime.now()
            )
            db.add(profile)
        
        db.commit()
        db.refresh(profile)
        
        return {
            "message": "온보딩 프로필 정보가 성공적으로 저장되었습니다.",
            "success": True,
            "profile": {
                "friend_type": profile.friend_type,
                "department": profile.department,
                "student_status": profile.student_status,
                "smoking": profile.smoking,
                "drinking": profile.drinking,
                "mbti": profile.mbti,
                "religion": profile.religion,
                "personality_keywords": json.loads(profile.personality_keywords) if profile.personality_keywords else [],
                "interest_keywords": json.loads(profile.interest_keywords) if profile.interest_keywords else [],
                "friend_style_keywords": json.loads(profile.friend_style_keywords) if profile.friend_style_keywords else []
            }
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온보딩 프로필 저장 중 오류가 발생했습니다."
        )

# =============================================================================
# 알람 시스템 API
# =============================================================================

@app.get("/notifications/", response_model=NotificationListResponse)
async def get_notifications(
    page: int = 1,
    size: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 알람 목록을 조회합니다."""
    try:
        # 기본 쿼리
        query = db.query(Notification).filter(Notification.user_id == current_user.user_id)
        
        # 읽지 않은 알람만 조회
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        # 전체 개수 조회
        total_count = query.count()
        
        # 읽지 않은 알람 개수 조회
        unread_count = db.query(Notification).filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read == False
        ).count()
        
        # 페이지네이션
        offset = (page - 1) * size
        notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(size).all()
        
        return NotificationListResponse(
            notifications=notifications,
            total_count=total_count,
            unread_count=unread_count
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알람 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/notifications/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 알람 통계를 조회합니다."""
    try:
        # 전체 알람 수
        total_count = db.query(Notification).filter(
            Notification.user_id == current_user.user_id
        ).count()
        
        # 읽지 않은 알람 수
        unread_count = db.query(Notification).filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read == False
        ).count()
        
        # 타입별 알람 수
        type_counts = {}
        for notification_type in NotificationTypeEnum:
            count = db.query(Notification).filter(
                Notification.user_id == current_user.user_id,
                Notification.notification_type == notification_type.value
            ).count()
            type_counts[notification_type.value] = count
        
        return NotificationStatsResponse(
            total_count=total_count,
            unread_count=unread_count,
            by_type=type_counts
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알람 통계 조회 중 오류가 발생했습니다."
        )

@app.post("/notifications/mark-read")
async def mark_notifications_read(
    request: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알람을 읽음 처리합니다."""
    try:
        # 사용자의 알람인지 확인하고 읽음 처리
        updated_count = db.query(Notification).filter(
            Notification.notification_id.in_(request.notification_ids),
            Notification.user_id == current_user.user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.read_at: datetime.now()
        })
        
        db.commit()
        
        return {
            "message": f"{updated_count}개의 알람이 읽음 처리되었습니다.",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알람 읽음 처리 중 오류가 발생했습니다."
        )

@app.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모든 알람을 읽음 처리합니다."""
    try:
        # 사용자의 모든 읽지 않은 알람을 읽음 처리
        updated_count = db.query(Notification).filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.read_at: datetime.now()
        })
        
        db.commit()
        
        return {
            "message": f"모든 알람({updated_count}개)이 읽음 처리되었습니다.",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="전체 알람 읽음 처리 중 오류가 발생했습니다."
        )

@app.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 알람을 삭제합니다."""
    try:
        # 알람 조회 및 소유권 확인
        notification = db.query(Notification).filter(
            Notification.notification_id == notification_id,
            Notification.user_id == current_user.user_id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="알람을 찾을 수 없습니다."
            )
        
        # 알람 삭제
        db.delete(notification)
        db.commit()
        
        return {"message": "알람이 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알람 삭제 중 오류가 발생했습니다."
        )

# 내부 함수: 알람 생성 (다른 API에서 호출용)
def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    data: str = None
):
    """내부 함수: 새 알람을 생성합니다."""
    try:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
        
    except Exception as e:
        db.rollback()
        return None

# =============================================================================
# 고급 채팅 기능 API
# =============================================================================

@app.post("/chat/upload/", response_model=FileUploadResponse)
async def upload_chat_file(
    room_id: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방에 파일 업로드"""
    try:
        from app.services.file_service import FileService
        from app.models.models import ChatParticipant
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 파일을 업로드할 권한이 없습니다."
            )
        
        # 파일 저장
        file_info = await FileService.save_chat_file(file, room_id, current_user.user_id)
        
        return FileUploadResponse(
            file_url=file_info["file_url"],
            file_name=file_info["file_name"],
            file_size=file_info["file_size"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 업로드 중 오류가 발생했습니다."
        )

@app.post("/chat/messages/{message_id}/reactions/", response_model=MessageReactionResponse)
async def add_message_reaction(
    message_id: int,
    reaction_data: MessageReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """메시지에 반응(이모지) 추가"""
    try:
        from app.models.models import ChatMessage, MessageReaction, ChatParticipant
        
        # 메시지 존재 확인
        message = db.query(ChatMessage).filter(
            ChatMessage.message_id == message_id,
            ChatMessage.is_deleted == False
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없습니다."
            )
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == message.room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 기존 반응이 있는지 확인 (같은 사용자, 같은 이모지)
        existing_reaction = db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == current_user.user_id,
            MessageReaction.emoji == reaction_data.emoji
        ).first()
        
        if existing_reaction:
            # 이미 반응이 있으면 제거
            db.delete(existing_reaction)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="반응이 제거되었습니다."
            )
        
        # 새 반응 추가
        new_reaction = MessageReaction(
            message_id=message_id,
            user_id=current_user.user_id,
            emoji=reaction_data.emoji
        )
        
        db.add(new_reaction)
        db.commit()
        db.refresh(new_reaction)
        
        # WebSocket으로 실시간 알림
        reaction_message = {
            "type": "reaction",
            "message_id": message_id,
            "user_id": current_user.user_id,
            "user_name": current_user.name,
            "emoji": reaction_data.emoji,
            "action": "add",
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast_to_room(json.dumps(reaction_message), message.room_id)
        
        return MessageReactionResponse(
            reaction_id=new_reaction.reaction_id,
            message_id=new_reaction.message_id,
            user_id=new_reaction.user_id,
            user_name=current_user.name,
            emoji=new_reaction.emoji,
            created_at=new_reaction.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 반응 추가 중 오류가 발생했습니다."
        )

@app.delete("/chat/messages/{message_id}/reactions/{emoji}")
async def remove_message_reaction(
    message_id: int,
    emoji: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """메시지 반응 제거"""
    try:
        from app.models.models import ChatMessage, MessageReaction, ChatParticipant
        
        # 메시지 존재 확인
        message = db.query(ChatMessage).filter(
            ChatMessage.message_id == message_id,
            ChatMessage.is_deleted == False
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없습니다."
            )
        
        # 반응 찾기
        reaction = db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == current_user.user_id,
            MessageReaction.emoji == emoji
        ).first()
        
        if not reaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 반응을 찾을 수 없습니다."
            )
        
        # 반응 제거
        db.delete(reaction)
        db.commit()
        
        # WebSocket으로 실시간 알림
        reaction_message = {
            "type": "reaction",
            "message_id": message_id,
            "user_id": current_user.user_id,
            "user_name": current_user.name,
            "emoji": emoji,
            "action": "remove",
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast_to_room(json.dumps(reaction_message), message.room_id)
        
        return {"detail": "반응이 제거되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 반응 제거 중 오류가 발생했습니다."
        )

@app.get("/chat/messages/{message_id}/reactions/", response_model=List[MessageReactionResponse])
async def get_message_reactions(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """메시지의 모든 반응 조회"""
    try:
        from app.models.models import ChatMessage, MessageReaction, ChatParticipant
        
        # 메시지 존재 확인
        message = db.query(ChatMessage).filter(
            ChatMessage.message_id == message_id,
            ChatMessage.is_deleted == False
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없습니다."
            )
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == message.room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 반응 목록 조회
        reactions = db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id
        ).all()
        
        reactions_response = []
        for reaction in reactions:
            user = db.query(User).filter(User.user_id == reaction.user_id).first()
            reactions_response.append(MessageReactionResponse(
                reaction_id=reaction.reaction_id,
                message_id=reaction.message_id,
                user_id=reaction.user_id,
                user_name=user.name if user else "Unknown",
                emoji=reaction.emoji,
                created_at=reaction.created_at
            ))
        
        return reactions_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 반응 조회 중 오류가 발생했습니다."
        )

@app.get("/chat/rooms/{room_id}/search/", response_model=MessageSearchResponse)
async def search_messages(
    room_id: int,
    q: str,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 내 메시지 검색"""
    try:
        from app.models.models import ChatMessage, ChatParticipant
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 메시지 검색
        search_query = f"%{q}%"
        offset = (page - 1) * size
        
        messages_query = db.query(ChatMessage).filter(
            ChatMessage.room_id == room_id,
            ChatMessage.is_deleted == False,
            ChatMessage.message_content.like(search_query)
        ).order_by(ChatMessage.created_at.desc())
        
        total_count = messages_query.count()
        messages = messages_query.offset(offset).limit(size).all()
        
        # 메시지 응답 생성
        messages_response = []
        for message in messages:
            sender = db.query(User).filter(User.user_id == message.sender_id).first()
            
            # 답장 메시지 정보 가져오기
            reply_to_message = None
            if message.reply_to_message_id:
                reply_msg = db.query(ChatMessage).filter(
                    ChatMessage.message_id == message.reply_to_message_id
                ).first()
                reply_to_message = reply_msg.message_content[:100] if reply_msg else None
            
            # 반응 정보 가져오기
            reactions = db.query(MessageReaction).filter(
                MessageReaction.message_id == message.message_id
            ).all()
            
            reactions_response = []
            for reaction in reactions:
                reaction_user = db.query(User).filter(User.user_id == reaction.user_id).first()
                reactions_response.append(MessageReactionResponse(
                    reaction_id=reaction.reaction_id,
                    message_id=reaction.message_id,
                    user_id=reaction.user_id,
                    user_name=reaction_user.name if reaction_user else "Unknown",
                    emoji=reaction.emoji,
                    created_at=reaction.created_at
                ))
            
            message_response = ChatMessageResponse(
                message_id=message.message_id,
                room_id=message.room_id,
                sender_id=message.sender_id,
                sender_name=sender.name if sender else "Unknown",
                message_content=message.message_content,
                message_type=message.message_type,
                file_url=message.file_url,
                file_name=message.file_name,
                file_size=message.file_size,
                reply_to_message_id=message.reply_to_message_id,
                reply_to_message=reply_to_message,
                is_edited=message.is_edited,
                is_deleted=message.is_deleted,
                edited_at=message.edited_at,
                reactions=reactions_response,
                created_at=message.created_at,
                updated_at=message.updated_at
            )
            messages_response.append(message_response)
        
        return MessageSearchResponse(
            messages=messages_response,
            total_count=total_count,
            page=page,
            has_more=total_count > page * size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 검색 중 오류가 발생했습니다."
        )

@app.get("/chat/rooms/{room_id}/settings/", response_model=ChatRoomSettingsResponse)
async def get_chat_room_settings(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 개인 설정 조회"""
    try:
        from app.models.models import ChatRoomSettings, ChatParticipant
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 설정 조회 (없으면 기본값으로 생성)
        settings = db.query(ChatRoomSettings).filter(
            ChatRoomSettings.room_id == room_id,
            ChatRoomSettings.user_id == current_user.user_id
        ).first()
        
        if not settings:
            # 기본 설정 생성
            settings = ChatRoomSettings(
                room_id=room_id,
                user_id=current_user.user_id
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return ChatRoomSettingsResponse(
            setting_id=settings.setting_id,
            room_id=settings.room_id,
            user_id=settings.user_id,
            notifications_enabled=settings.notifications_enabled,
            notification_sound=settings.notification_sound,
            background_theme=settings.background_theme,
            font_size=settings.font_size,
            auto_download_images=settings.auto_download_images,
            auto_download_files=settings.auto_download_files,
            created_at=settings.created_at,
            updated_at=settings.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 설정 조회 중 오류가 발생했습니다."
        )

@app.put("/chat/rooms/{room_id}/settings/", response_model=ChatRoomSettingsResponse)
async def update_chat_room_settings(
    room_id: int,
    settings_data: ChatRoomSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 개인 설정 업데이트"""
    try:
        from app.models.models import ChatRoomSettings, ChatParticipant
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 설정 조회 또는 생성
        settings = db.query(ChatRoomSettings).filter(
            ChatRoomSettings.room_id == room_id,
            ChatRoomSettings.user_id == current_user.user_id
        ).first()
        
        if not settings:
            settings = ChatRoomSettings(
                room_id=room_id,
                user_id=current_user.user_id
            )
            db.add(settings)
        
        # 설정 업데이트
        update_data = settings_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        
        db.commit()
        db.refresh(settings)
        
        return ChatRoomSettingsResponse(
            setting_id=settings.setting_id,
            room_id=settings.room_id,
            user_id=settings.user_id,
            notifications_enabled=settings.notifications_enabled,
            notification_sound=settings.notification_sound,
            background_theme=settings.background_theme,
            font_size=settings.font_size,
            auto_download_images=settings.auto_download_images,
            auto_download_files=settings.auto_download_files,
            created_at=settings.created_at,
            updated_at=settings.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 설정 업데이트 중 오류가 발생했습니다."
        )

@app.post("/chat/rooms/{room_id}/scheduled-messages/", response_model=ScheduledMessageResponse)
async def create_scheduled_message(
    room_id: int,
    message_data: ScheduledMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """예약 메시지 생성"""
    try:
        from app.models.models import ScheduledMessage, ChatParticipant
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 예약 시간 검증 (과거 시간 불가)
        if message_data.scheduled_time <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="예약 시간은 현재 시간보다 이후여야 합니다."
            )
        
        # 예약 메시지 생성
        scheduled_message = ScheduledMessage(
            room_id=room_id,
            sender_id=current_user.user_id,
            message_content=message_data.message_content,
            message_type=message_data.message_type,
            scheduled_time=message_data.scheduled_time
        )
        
        db.add(scheduled_message)
        db.commit()
        db.refresh(scheduled_message)
        
        return ScheduledMessageResponse(
            scheduled_id=scheduled_message.scheduled_id,
            room_id=scheduled_message.room_id,
            sender_id=scheduled_message.sender_id,
            message_content=scheduled_message.message_content,
            message_type=scheduled_message.message_type,
            file_url=scheduled_message.file_url,
            file_name=scheduled_message.file_name,
            scheduled_time=scheduled_message.scheduled_time,
            is_sent=scheduled_message.is_sent,
            sent_at=scheduled_message.sent_at,
            created_at=scheduled_message.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="예약 메시지 생성 중 오류가 발생했습니다."
        )

@app.get("/chat/rooms/{room_id}/online-status/", response_model=List[UserOnlineStatusResponse])
async def get_room_participants_status(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 참여자들의 온라인 상태 조회"""
    try:
        from app.models.models import ChatParticipant, UserOnlineStatus
        
        # 채팅방 참여 권한 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 채팅방에 접근할 권한이 없습니다."
            )
        
        # 참여자 목록과 온라인 상태 조회
        participants = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.is_active == True
        ).all()
        
        status_response = []
        for participant in participants:
            user = db.query(User).filter(User.user_id == participant.user_id).first()
            if not user:
                continue
                
            # 온라인 상태 조회
            online_status = db.query(UserOnlineStatus).filter(
                UserOnlineStatus.user_id == participant.user_id
            ).first()
            
            status_response.append(UserOnlineStatusResponse(
                user_id=user.user_id,
                user_name=user.name,
                is_online=online_status.is_online if online_status else False,
                last_seen=online_status.last_seen if online_status else user.created_at,
                status_message=online_status.status_message if online_status else None
            ))
        
        return status_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="온라인 상태 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 이미지 업로드 시스템
# =============================================================================

@app.post("/api/users/images/upload")
async def upload_user_images(
    images: List[UploadFile] = File(...),
    primary_image_index: int = Form(0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 이미지 업로드"""
    try:
        if not images:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드할 이미지가 없습니다."
            )
        
        if len(images) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최대 5장까지만 업로드할 수 있습니다."
            )
        
        # 기존 이미지들 삭제 (새로 업로드하는 경우)
        existing_images = db.query(UserImage).filter(UserImage.user_id == current_user.user_id).all()
        for img in existing_images:
            db.delete(img)
        
        uploaded_images = []
        primary_image_id = None
        
        for i, image in enumerate(images):
            # 파일 크기 검증 (10MB 제한)
            if image.size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미지 크기는 10MB 이하여야 합니다. ({image.filename})"
                )
            
            # 파일 확장자 검증
            if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"지원하지 않는 파일 형식입니다. JPG, PNG, WebP만 가능합니다. ({image.filename})"
                )
            
            # 파일 저장
            file_extension = image.filename.split('.')[-1].lower()
            file_name = f"profile_{current_user.user_id}_{i+1}.{file_extension}"
            file_path = f"static/images/profiles/{current_user.user_id}/{file_name}"
            
            # 디렉토리 생성
            import os
            os.makedirs(f"static/images/profiles/{current_user.user_id}", exist_ok=True)
            
            # 파일 저장
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            # 데이터베이스에 이미지 정보 저장
            is_primary = (i == primary_image_index)
            user_image = UserImage(
                user_id=current_user.user_id,
                image_url=f"/{file_path}",
                is_primary=is_primary,
                upload_order=i + 1,
                file_name=image.filename,
                file_size=len(content),
                created_at=datetime.now()
            )
            
            db.add(user_image)
            db.flush()  # ID 생성
            
            if is_primary:
                primary_image_id = user_image.image_id
            
            uploaded_images.append({
                "image_id": user_image.image_id,
                "image_url": user_image.image_url,
                "file_name": user_image.file_name,
                "file_size": user_image.file_size,
                "is_primary": user_image.is_primary,
                "upload_order": user_image.upload_order
            })
        
        # 온보딩 프로필이 있다면 이미지 업로드 완료로 표시
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()
        if profile:
            profile.onboarding_completed = True
            profile.onboarding_completed_at = datetime.now()
        
        db.commit()
        
        return {
            "message": "프로필 이미지가 성공적으로 업로드되었습니다.",
            "uploaded_images": uploaded_images,
            "total_images": len(uploaded_images),
            "primary_image_id": primary_image_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 업로드 중 오류가 발생했습니다."
        )

@app.get("/api/users/{user_id}/profile/images")
async def get_user_profile_images(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 이미지 목록 조회"""
    try:
        # 권한 확인 (본인만 조회 가능)
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 프로필 이미지만 조회할 수 있습니다."
            )
        
        images = db.query(UserImage).filter(UserImage.user_id == user_id).order_by(UserImage.upload_order).all()
        
        primary_image_id = None
        for img in images:
            if img.is_primary:
                primary_image_id = img.image_id
                break
        
        return {
            "images": [
                {
                    "image_id": img.image_id,
                    "image_url": img.image_url,
                    "file_name": img.file_name,
                    "file_size": img.file_size,
                    "is_primary": img.is_primary,
                    "upload_order": img.upload_order,
                    "created_at": img.created_at
                }
                for img in images
            ],
            "total_count": len(images),
            "primary_image_id": primary_image_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 목록 조회 중 오류가 발생했습니다."
        )

@app.delete("/api/users/{user_id}/profile/images/{image_id}")
async def delete_user_profile_image(
    user_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 이미지 삭제"""
    try:
        # 권한 확인 (본인만 삭제 가능)
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 프로필 이미지만 삭제할 수 있습니다."
            )
        
        # 이미지 조회
        image = db.query(UserImage).filter(
            UserImage.image_id == image_id,
            UserImage.user_id == user_id
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 대표 이미지인 경우 삭제 불가
        if image.is_primary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="대표 이미지는 삭제할 수 없습니다. 먼저 다른 이미지를 대표로 설정해주세요."
            )
        
        # 파일 삭제
        import os
        if os.path.exists(image.image_url.lstrip('/')):
            os.remove(image.image_url.lstrip('/'))
        
        # 데이터베이스에서 삭제
        db.delete(image)
        db.commit()
        
        return {
            "message": "이미지가 성공적으로 삭제되었습니다.",
            "deleted_image_id": image_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 삭제 중 오류가 발생했습니다."
        )

@app.put("/api/users/{user_id}/profile/images/{image_id}/primary")
async def set_primary_image(
    user_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """대표 이미지 설정"""
    try:
        # 권한 확인 (본인만 설정 가능)
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 프로필 이미지만 설정할 수 있습니다."
            )
        
        # 이미지 조회
        target_image = db.query(UserImage).filter(
            UserImage.image_id == image_id,
            UserImage.user_id == user_id
        ).first()
        
        if not target_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 기존 대표 이미지 해제
        previous_primary = db.query(UserImage).filter(
            UserImage.user_id == user_id,
            UserImage.is_primary == True
        ).first()
        
        if previous_primary:
            previous_primary.is_primary = False
        
        # 새로운 대표 이미지 설정
        target_image.is_primary = True
        
        db.commit()
        
        return {
            "message": "대표 이미지가 변경되었습니다.",
            "new_primary_image_id": image_id,
            "previous_primary_image_id": previous_primary.image_id if previous_primary else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대표 이미지 설정 중 오류가 발생했습니다."
        )

# =============================================================================
# 시간표 수정/삭제 및 특정 시간표의 과목 조회
# =============================================================================

@app.put("/timetables/{timetable_id}", response_model=TimetableResponse)
async def update_timetable(
    timetable_id: int,
    timetable_data: TimetableUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시간표를 수정합니다."""
    try:
        timetable = db.query(Timetable).filter(
            Timetable.timetable_id == timetable_id,
            Timetable.user_id == current_user.user_id
        ).first()
        
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시간표를 찾을 수 없습니다."
            )
        
        # 업데이트할 필드만 수정
        if timetable_data.semester is not None:
            timetable.semester = timetable_data.semester
        if timetable_data.year is not None:
            timetable.year = timetable_data.year
        if timetable_data.is_active is not None:
            # 활성 시간표 변경 시 기존 활성 시간표 비활성화
            if timetable_data.is_active:
                db.query(Timetable).filter(
                    Timetable.user_id == current_user.user_id,
                    Timetable.is_active == True,
                    Timetable.timetable_id != timetable_id
                ).update({"is_active": False})
            timetable.is_active = timetable_data.is_active
        
        db.commit()
        db.refresh(timetable)
        
        return timetable
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표 수정 중 오류가 발생했습니다."
        )

@app.delete("/timetables/{timetable_id}")
async def delete_timetable(
    timetable_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시간표를 삭제합니다."""
    try:
        timetable = db.query(Timetable).filter(
            Timetable.timetable_id == timetable_id,
            Timetable.user_id == current_user.user_id
        ).first()
        
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시간표를 찾을 수 없습니다."
            )
        
        # 연결된 과목 관계 삭제
        db.query(TimetableSubject).filter(
            TimetableSubject.timetable_id == timetable_id
        ).delete()
        
        # 시간표 삭제
        db.delete(timetable)
        db.commit()
        
        return {"message": "시간표가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표 삭제 중 오류가 발생했습니다."
        )

@app.get("/timetables/{timetable_id}/subjects/", response_model=list[SubjectResponse])
async def get_timetable_subjects(
    timetable_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 시간표의 과목 목록을 조회합니다."""
    try:
        # 시간표 소유권 확인
        timetable = db.query(Timetable).filter(
            Timetable.timetable_id == timetable_id,
            Timetable.user_id == current_user.user_id
        ).first()
        
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시간표를 찾을 수 없습니다."
            )
        
        # 시간표에 연결된 과목들 조회
        timetable_subjects = db.query(TimetableSubject).filter(
            TimetableSubject.timetable_id == timetable_id
        ).all()
        
        subjects = []
        for ts in timetable_subjects:
            subject = db.query(Subject).filter(Subject.subject_id == ts.subject_id).first()
            if subject:
                subjects.append(SubjectResponse(
                    subject_id=subject.subject_id,
                    user_id=subject.user_id,
                    subject_name=subject.subject_name,
                    professor_name=subject.professor_name,
                    classroom=subject.classroom,
                    day_of_week=subject.day_of_week,
                    start_time=subject.start_time,
                    end_time=subject.end_time,
                    created_at=subject.created_at
                ))
        
        return subjects
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간표 과목 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 채팅 메시지 REST API 전송 및 수정/삭제
# =============================================================================

@app.post("/chat/rooms/{room_id}/messages/", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_message(
    room_id: int,
    message_data: ChatMessageCreate,
    reply_to_message_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """REST API로 채팅 메시지를 전송합니다."""
    try:
        # 채팅방 존재 및 참여 여부 확인
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="채팅방에 참여하지 않았거나 접근 권한이 없습니다."
            )
        
        # 답장 메시지 확인
        reply_to = None
        if reply_to_message_id:
            reply_to = db.query(ChatMessage).filter(
                ChatMessage.message_id == reply_to_message_id,
                ChatMessage.room_id == room_id
            ).first()
            if not reply_to:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="답장할 메시지를 찾을 수 없습니다."
                )
        
        # 메시지 생성
        message = ChatMessage(
            room_id=room_id,
            sender_id=current_user.user_id,
            message_content=message_data.message_content,
            message_type=message_data.message_type.value,
            reply_to_message_id=reply_to_message_id if reply_to else None
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # 응답 생성
        return ChatMessageResponse(
            message_id=message.message_id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            sender_name=current_user.name,
            message_content=message.message_content,
            message_type=message.message_type,
            file_url=message.file_url,
            file_name=message.file_name,
            file_size=message.file_size,
            reply_to_message_id=message.reply_to_message_id,
            reply_to_message=reply_to.message_content if reply_to else None,
            is_edited=message.is_edited,
            is_deleted=message.is_deleted,
            edited_at=message.edited_at,
            reactions=[],
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 전송 중 오류가 발생했습니다."
        )

@app.put("/chat/messages/{message_id}", response_model=ChatMessageResponse)
async def update_chat_message(
    message_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅 메시지를 수정합니다."""
    try:
        message = db.query(ChatMessage).filter(
            ChatMessage.message_id == message_id,
            ChatMessage.sender_id == current_user.user_id,
            ChatMessage.is_deleted == False
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없거나 수정 권한이 없습니다."
            )
        
        # 메시지 수정
        message.message_content = message_data.message_content
        message.is_edited = True
        message.edited_at = datetime.now()
        
        db.commit()
        db.refresh(message)
        
        # 응답 생성
        sender = db.query(User).filter(User.user_id == message.sender_id).first()
        reactions = db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id
        ).all()
        
        reaction_responses = []
        for reaction in reactions:
            user = db.query(User).filter(User.user_id == reaction.user_id).first()
            reaction_responses.append(MessageReactionResponse(
                reaction_id=reaction.reaction_id,
                message_id=reaction.message_id,
                user_id=reaction.user_id,
                user_name=user.name if user else "알 수 없음",
                emoji=reaction.emoji,
                created_at=reaction.created_at
            ))
        
        return ChatMessageResponse(
            message_id=message.message_id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            sender_name=sender.name if sender else "알 수 없음",
            message_content=message.message_content,
            message_type=message.message_type,
            file_url=message.file_url,
            file_name=message.file_name,
            file_size=message.file_size,
            reply_to_message_id=message.reply_to_message_id,
            reply_to_message=None,
            is_edited=message.is_edited,
            is_deleted=message.is_deleted,
            edited_at=message.edited_at,
            reactions=reaction_responses,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 수정 중 오류가 발생했습니다."
        )

@app.delete("/chat/messages/{message_id}")
async def delete_chat_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅 메시지를 삭제합니다."""
    try:
        message = db.query(ChatMessage).filter(
            ChatMessage.message_id == message_id,
            ChatMessage.sender_id == current_user.user_id
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없거나 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        message.is_deleted = True
        message.message_content = "(삭제된 메시지입니다)"
        
        db.commit()
        
        return {"message": "메시지가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 삭제 중 오류가 발생했습니다."
        )

# =============================================================================
# 채팅방 관리 기능
# =============================================================================

@app.put("/chat/rooms/{room_id}/", response_model=ChatRoomResponse)
async def update_chat_room(
    room_id: int,
    room_data: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 정보를 수정합니다."""
    try:
        room = db.query(ChatRoom).filter(ChatRoom.room_id == room_id).first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )
        
        # 권한 확인 (생성자 또는 관리자만 수정 가능)
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id
        ).first()
        
        if not participant or (room.created_by != current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="채팅방 수정 권한이 없습니다."
            )
        
        # 채팅방 정보 수정
        room.room_name = room_data.room_name
        room.room_type = room_data.room_type.value
        
        db.commit()
        db.refresh(room)
        
        # 참여자 수 계산
        participant_count = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.is_active == True
        ).count()
        
        return ChatRoomResponse(
            room_id=room.room_id,
            room_name=room.room_name,
            room_type=room.room_type,
            created_by=room.created_by,
            is_active=room.is_active,
            created_at=room.created_at,
            updated_at=room.updated_at,
            participant_count=participant_count,
            last_message=None,
            unread_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 수정 중 오류가 발생했습니다."
        )

@app.post("/chat/rooms/{room_id}/leave/")
async def leave_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방을 나갑니다."""
    try:
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방에 참여하지 않았습니다."
            )
        
        # 채팅방 나가기
        participant.is_active = False
        participant.left_at = datetime.now()
        
        db.commit()
        
        return {"message": "채팅방을 나갔습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 나가기 중 오류가 발생했습니다."
        )

@app.delete("/chat/rooms/{room_id}/")
async def delete_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방을 삭제합니다."""
    try:
        room = db.query(ChatRoom).filter(ChatRoom.room_id == room_id).first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )
        
        # 생성자만 삭제 가능
        if room.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="채팅방 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        room.is_active = False
        
        db.commit()
        
        return {"message": "채팅방이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 삭제 중 오류가 발생했습니다."
        )

@app.post("/chat/rooms/{room_id}/participants/")
async def add_chat_participant(
    room_id: int,
    user_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방에 참여자를 추가합니다."""
    try:
        room = db.query(ChatRoom).filter(ChatRoom.room_id == room_id).first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )
        
        # 권한 확인 (생성자 또는 관리자만 추가 가능)
        if room.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="참여자 추가 권한이 없습니다."
            )
        
        # 사용자 존재 확인
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 이미 참여 중인지 확인
        existing = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == user_id
        ).first()
        
        if existing:
            if existing.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 참여 중인 사용자입니다."
                )
            else:
                # 재참여
                existing.is_active = True
                existing.left_at = None
                existing.joined_at = datetime.now()
        else:
            # 새 참여자 추가
            participant = ChatParticipant(
                room_id=room_id,
                user_id=user_id,
                is_active=True
            )
            db.add(participant)
        
        db.commit()
        
        return {"message": "참여자가 추가되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="참여자 추가 중 오류가 발생했습니다."
        )

@app.delete("/chat/rooms/{room_id}/participants/{user_id}")
async def remove_chat_participant(
    room_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방에서 참여자를 제거합니다."""
    try:
        room = db.query(ChatRoom).filter(ChatRoom.room_id == room_id).first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )
        
        # 권한 확인 (생성자 또는 관리자만 제거 가능, 또는 본인)
        if room.created_by != current_user.user_id and current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="참여자 제거 권한이 없습니다."
            )
        
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == user_id
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="참여자를 찾을 수 없습니다."
            )
        
        # 참여자 제거
        participant.is_active = False
        participant.left_at = datetime.now()
        
        db.commit()
        
        return {"message": "참여자가 제거되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="참여자 제거 중 오류가 발생했습니다."
        )

# =============================================================================
# 사용자 관리 기능
# =============================================================================

@app.get("/api/users/search/", response_model=UserSearchListResponse)
async def search_users(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 20
):
    """사용자를 검색합니다."""
    try:
        # 이름 또는 이메일로 검색
        search_pattern = f"%{query}%"
        users = db.query(User).filter(
            (User.name.like(search_pattern)) | (User.email.like(search_pattern))
        ).offset((page - 1) * size).limit(size).all()
        
        # 프로필 정보 포함
        results = []
        for user in users:
            # 차단된 사용자 제외
            blocked = db.query(UserBlock).filter(
                UserBlock.blocker_id == current_user.user_id,
                UserBlock.blocked_id == user.user_id
            ).first()
            if blocked:
                continue
            
            # 프로필 정보 조회
            profile = db.query(UserProfile).filter(UserProfile.user_id == user.user_id).first()
            primary_image = db.query(UserImage).filter(
                UserImage.user_id == user.user_id,
                UserImage.is_primary == True
            ).first()
            
            results.append(UserSearchResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                department=profile.department if profile else None,
                profile_image=primary_image.image_url if primary_image else None
            ))
        
        return UserSearchListResponse(
            users=results,
            total_count=len(results)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 검색 중 오류가 발생했습니다."
        )

@app.put("/auth/change-password/")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """비밀번호를 변경합니다."""
    try:
        # 현재 비밀번호 확인
        from app.auth.security import verify_password
        if not verify_password(password_data.current_password, current_user.password_hash, current_user.salt):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="현재 비밀번호가 올바르지 않습니다."
            )
        
        # 새 비밀번호 해시
        new_salt = generate_salt()
        new_password_hash = hash_password_with_salt(password_data.new_password, new_salt)
        
        # 비밀번호 업데이트
        current_user.password_hash = new_password_hash
        current_user.salt = new_salt
        
        db.commit()
        
        return {"message": "비밀번호가 변경되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경 중 오류가 발생했습니다."
        )

@app.delete("/auth/account/")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """계정을 탈퇴합니다."""
    try:
        # 소프트 삭제 (실제로는 is_active 같은 플래그를 사용하는 것이 좋지만, 여기서는 실제 삭제)
        # 관련 데이터도 함께 처리해야 함
        
        # 사용자 관련 데이터 삭제 (선택적)
        # 실제 운영에서는 소프트 삭제를 권장
        
        db.delete(current_user)
        db.commit()
        
        return {"message": "계정이 삭제되었습니다."}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 탈퇴 중 오류가 발생했습니다."
        )

@app.post("/api/users/{user_id}/block/")
async def block_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자를 차단합니다."""
    try:
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자기 자신을 차단할 수 없습니다."
            )
        
        # 사용자 존재 확인
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 이미 차단되어 있는지 확인
        existing = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.user_id,
            UserBlock.blocked_id == user_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 차단된 사용자입니다."
            )
        
        # 차단 추가
        block = UserBlock(
            blocker_id=current_user.user_id,
            blocked_id=user_id
        )
        db.add(block)
        db.commit()
        
        return {"message": "사용자가 차단되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 차단 중 오류가 발생했습니다."
        )

@app.delete("/api/users/{user_id}/block/")
async def unblock_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 차단을 해제합니다."""
    try:
        block = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.user_id,
            UserBlock.blocked_id == user_id
        ).first()
        
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="차단된 사용자가 아닙니다."
            )
        
        db.delete(block)
        db.commit()
        
        return {"message": "차단이 해제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="차단 해제 중 오류가 발생했습니다."
        )

@app.get("/api/users/blocked/", response_model=UserBlockListResponse)
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """차단된 사용자 목록을 조회합니다."""
    try:
        blocks = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.user_id
        ).all()
        
        blocked_users = []
        for block in blocks:
            user = db.query(User).filter(User.user_id == block.blocked_id).first()
            if user:
                blocked_users.append(UserBlockResponse(
                    block_id=block.block_id,
                    blocked_id=block.blocked_id,
                    blocked_name=user.name,
                    created_at=block.created_at
                ))
        
        return UserBlockListResponse(
            blocked_users=blocked_users,
            total_count=len(blocked_users)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="차단 목록 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 알림 설정 API
# =============================================================================

@app.get("/api/users/notification-settings/", response_model=UserNotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 설정을 조회합니다."""
    try:
        settings = db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == current_user.user_id
        ).first()
        
        if not settings:
            # 기본 설정 생성
            settings = UserNotificationSettings(
                user_id=current_user.user_id
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return settings
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 설정 조회 중 오류가 발생했습니다."
        )

@app.put("/api/users/notification-settings/", response_model=UserNotificationSettingsResponse)
async def update_notification_settings(
    settings_data: UserNotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 설정을 업데이트합니다."""
    try:
        settings = db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == current_user.user_id
        ).first()
        
        if not settings:
            settings = UserNotificationSettings(user_id=current_user.user_id)
            db.add(settings)
        
        # 업데이트할 필드만 수정
        if settings_data.push_enabled is not None:
            settings.push_enabled = settings_data.push_enabled
        if settings_data.chat_notifications is not None:
            settings.chat_notifications = settings_data.chat_notifications
        if settings_data.timetable_notifications is not None:
            settings.timetable_notifications = settings_data.timetable_notifications
        if settings_data.match_notifications is not None:
            settings.match_notifications = settings_data.match_notifications
        if settings_data.system_notifications is not None:
            settings.system_notifications = settings_data.system_notifications
        if settings_data.reminder_notifications is not None:
            settings.reminder_notifications = settings_data.reminder_notifications
        
        db.commit()
        db.refresh(settings)
        
        return settings
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 설정 업데이트 중 오류가 발생했습니다."
        )

# =============================================================================
# 그룹/워크스페이스 시스템 API
# =============================================================================

# ⚠️ 이 API는 중복입니다. Line 7424의 get_group_detail을 사용하세요.
# 삭제됨: 오래된 get_group API (Phase 1 필드 없음)

@app.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group_data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 정보를 수정합니다."""
    try:
        group = db.query(Group).filter(Group.group_id == group_id).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 권한 확인 (owner 또는 admin만 수정 가능)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if not member and group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 수정 권한이 없습니다."
            )
        
        # 업데이트
        if group_data.group_name is not None:
            group.group_name = group_data.group_name
        if group_data.description is not None:
            group.description = group_data.description
        if group_data.is_public is not None:
            group.is_public = group_data.is_public
        if group_data.requires_approval is not None:
            group.requires_approval = group_data.requires_approval
        if group_data.max_members is not None:
            group.max_members = group_data.max_members
        
        # Phase 1 필드 업데이트
        if group_data.category is not None:
            group.category = group_data.category
        if group_data.tags is not None:
            group.tags = json.dumps(group_data.tags, ensure_ascii=False) if group_data.tags else None
        if group_data.primary_image_url is not None:
            group.primary_image_url = group_data.primary_image_url
        if group_data.is_regular is not None:
            group.is_regular = group_data.is_regular
        if group_data.regular_weekday is not None:
            group.regular_weekday = json.dumps(group_data.regular_weekday) if group_data.regular_weekday else None
        if group_data.regular_time is not None:
            group.regular_time = group_data.regular_time
        if group_data.regular_location is not None:
            group.regular_location = group_data.regular_location
        if group_data.rules is not None:
            group.rules = json.dumps(group_data.rules, ensure_ascii=False) if group_data.rules else None
        if group_data.activity_plan is not None:
            group.activity_plan = json.dumps(group_data.activity_plan, ensure_ascii=False) if group_data.activity_plan else None
        
        db.commit()
        db.refresh(group)
        
        
        creator = db.query(User).filter(User.user_id == group.created_by).first()
        member_count = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        ).count()
        
        like_count = db.query(GroupLike).filter(
            GroupLike.group_id == group_id
        ).count()
        
        is_liked = db.query(GroupLike).filter(
            GroupLike.group_id == group_id,
            GroupLike.user_id == current_user.user_id
        ).first() is not None
        
        pending_requests = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.role == 'pending'
        ).count()
        
        # tags를 JSON에서 리스트로 변환
        tags_list = []
        if group.tags:
            try:
                tags_list = json.loads(group.tags) if isinstance(group.tags, str) else group.tags
            except:
                tags_list = []
        
        # regular_weekday를 JSON에서 리스트로 변환
        weekday_list = []
        if group.regular_weekday:
            try:
                weekday_list = json.loads(group.regular_weekday) if isinstance(group.regular_weekday, str) else group.regular_weekday
            except:
                weekday_list = []
        
        # rules를 JSON에서 리스트로 변환
        rules_list = []
        if group.rules:
            try:
                rules_list = json.loads(group.rules) if isinstance(group.rules, str) else group.rules
            except:
                rules_list = []
        
        # activity_plan을 JSON에서 리스트로 변환
        activity_plan_list = []
        if group.activity_plan:
            try:
                activity_plan_list = json.loads(group.activity_plan) if isinstance(group.activity_plan, str) else group.activity_plan
            except:
                activity_plan_list = []
        
        # 한글 요일 표시 생성
        weekday_display = weekdays_to_korean(weekday_list)
        
        return GroupResponse(
            group_id=group.group_id,
            group_name=group.group_name,
            description=group.description,
            is_public=group.is_public,
            requires_approval=group.requires_approval,
            max_members=group.max_members,
            category=group.category,
            tags=tags_list,
            primary_image_url=group.primary_image_url,
            is_regular=group.is_regular,
            regular_weekday=weekday_list,
            regular_weekday_display=weekday_display,
            regular_time=group.regular_time,
            regular_location=group.regular_location,
            rules=rules_list,
            activity_plan=activity_plan_list,
            created_by=group.created_by,
            creator_name=creator.name if creator else "알 수 없음",
            is_active=group.is_active,
            member_count=member_count,
            like_count=like_count,
            is_liked=is_liked,
            view_count=group.view_count,
            pending_requests=pending_requests,
            created_at=group.created_at,
            updated_at=group.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="그룹 수정 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹을 삭제합니다."""
    try:
        group = db.query(Group).filter(Group.group_id == group_id).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # owner만 삭제 가능
        if group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        group.is_active = False
        db.commit()
        
        return {"message": "그룹이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="그룹 삭제 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/join/")
async def join_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹에 가입합니다."""
    try:
        group = db.query(Group).filter(Group.group_id == group_id).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 이미 가입했는지 확인
        existing = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id
        ).first()
        
        if existing:
            if existing.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 가입한 그룹입니다."
                )
            else:
                # 재가입
                existing.is_active = True
                existing.status = 'approved' if not group.requires_approval else 'pending'
                existing.left_at = None
        else:
            # 새 가입
            member = GroupMember(
                group_id=group_id,
                user_id=current_user.user_id,
                role='member',
                status='approved' if not group.requires_approval else 'pending'
            )
            db.add(member)
        
        db.commit()
        
        status_msg = "가입 신청이 완료되었습니다." if group.requires_approval else "가입이 완료되었습니다."
        return {"message": status_msg}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="그룹 가입 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/leave/")
async def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹을 탈퇴합니다."""
    try:
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="가입하지 않은 그룹입니다."
            )
        
        # owner는 탈퇴 불가 (그룹 삭제만 가능)
        if member.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="그룹 소유자는 탈퇴할 수 없습니다. 그룹을 삭제해주세요."
            )
        
        member.is_active = False
        member.left_at = datetime.now()
        
        db.commit()
        
        return {"message": "그룹을 탈퇴했습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="그룹 탈퇴 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/members/", response_model=GroupMemberListResponse)
async def get_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 멤버 목록을 조회합니다."""
    try:
        # 그룹 접근 권한 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        members = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        ).all()
        
        results = []
        for member in members:
            user = db.query(User).filter(User.user_id == member.user_id).first()
            if user:
                results.append(GroupMemberResponse(
                    member_id=member.member_id,
                    group_id=member.group_id,
                    user_id=member.user_id,
                    user_name=user.name,
                    role=member.role,
                    status=member.status,
                    joined_at=member.joined_at
                ))
        
        return GroupMemberListResponse(members=results, total_count=len(results))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="멤버 목록 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 매칭 시스템 API
# =============================================================================

@app.get("/matching/recommendations/", response_model=MatchingRecommendationListResponse)
async def get_matching_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 20
):
    """매칭 추천 목록을 조회합니다."""
    try:
        # 현재 사용자 프로필
        current_profile = db.query(UserProfile).filter(
            UserProfile.user_id == current_user.user_id
        ).first()
        
        if not current_profile:
            return MatchingRecommendationListResponse(recommendations=[], total_count=0)
        
        # 차단된 사용자 제외
        blocked_ids = [b.blocked_id for b in db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.user_id
        ).all()]
        
        # 이미 친구인 사용자 제외
        friend_ids = set()
        friendships = db.query(FriendRelationship).filter(
            (FriendRelationship.user1_id == current_user.user_id) |
            (FriendRelationship.user2_id == current_user.user_id),
            FriendRelationship.is_active == True
        ).all()
        for f in friendships:
            if f.user1_id == current_user.user_id:
                friend_ids.add(f.user2_id)
            else:
                friend_ids.add(f.user1_id)
        
        # 추천 사용자 조회 (간단한 구현 - 실제로는 더 복잡한 알고리즘 필요)
        users = db.query(User).filter(
            User.user_id != current_user.user_id,
            User.user_id.notin_(blocked_ids),
            User.user_id.notin_(friend_ids)
        ).offset((page - 1) * size).limit(size).all()
        
        results = []
        for user in users:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user.user_id).first()
            if not profile:
                continue
            
            # 공통 관심사 계산
            current_interests = json.loads(current_profile.interest_keywords) if current_profile.interest_keywords else []
            user_interests = json.loads(profile.interest_keywords) if profile.interest_keywords else []
            common = list(set(current_interests) & set(user_interests))
            
            # 프로필 이미지
            images = db.query(UserImage).filter(
                UserImage.user_id == user.user_id
            ).order_by(UserImage.upload_order).all()
            
            image_responses = []
            for img in images:
                image_responses.append(UserImageResponse(
                    image_id=img.image_id,
                    image_url=img.image_url,
                    is_primary=img.is_primary,
                    upload_order=img.upload_order,
                    file_name=img.file_name,
                    file_size=img.file_size,
                    created_at=img.created_at
                ))
            
            results.append(MatchingRecommendationResponse(
                user_id=user.user_id,
                name=user.name,
                department=profile.department,
                mbti=profile.mbti,
                profile_images=image_responses,
                common_interests=common
            ))
        
        return MatchingRecommendationListResponse(
            recommendations=results,
            total_count=len(results)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="매칭 추천 조회 중 오류가 발생했습니다."
        )

@app.post("/matching/requests/", response_model=MatchingRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_matching_request(
    request_data: MatchingRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """매칭 요청을 생성합니다."""
    try:
        if request_data.requested_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자기 자신에게 매칭 요청을 보낼 수 없습니다."
            )
        
        # 사용자 존재 확인
        requested_user = db.query(User).filter(User.user_id == request_data.requested_id).first()
        if not requested_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 이미 요청했는지 확인
        existing = db.query(MatchingRequest).filter(
            MatchingRequest.requester_id == current_user.user_id,
            MatchingRequest.requested_id == request_data.requested_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 매칭 요청을 보냈습니다."
            )
        
        # 매칭 요청 생성
        request = MatchingRequest(
            requester_id=current_user.user_id,
            requested_id=request_data.requested_id,
            status='pending'
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        
        requester = db.query(User).filter(User.user_id == request.requester_id).first()
        requested = db.query(User).filter(User.user_id == request.requested_id).first()
        
        return MatchingRequestResponse(
            request_id=request.request_id,
            requester_id=request.requester_id,
            requester_name=requester.name if requester else "알 수 없음",
            requested_id=request.requested_id,
            requested_name=requested.name if requested else "알 수 없음",
            status=request.status,
            created_at=request.created_at,
            updated_at=request.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="매칭 요청 생성 중 오류가 발생했습니다."
        )

@app.post("/matching/requests/{request_id}/accept/")
async def accept_matching_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """매칭 요청을 수락하고 자동으로 채팅방을 생성합니다."""
    try:
        matching_request = db.query(MatchingRequest).filter(
            MatchingRequest.request_id == request_id,
            MatchingRequest.requested_id == current_user.user_id,
            MatchingRequest.status == 'pending'
        ).first()
        
        if not matching_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="매칭 요청을 찾을 수 없습니다."
            )
        
        # 요청 상태 변경
        matching_request.status = 'accepted'
        
        # 친구 관계 생성
        friend = FriendRelationship(
            user1_id=matching_request.requester_id,
            user2_id=matching_request.requested_id,
            is_active=True
        )
        db.add(friend)
        
        # 채팅방 자동 생성 (이미 존재하는지 확인)
        existing_room = db.query(ChatRoom).join(ChatParticipant).filter(
            ChatRoom.room_type == 'direct',
            ChatRoom.is_active == True
        ).filter(
            ChatParticipant.user_id.in_([matching_request.requester_id, matching_request.requested_id])
        ).group_by(ChatRoom.room_id).having(
            func.count(ChatParticipant.user_id) == 2
        ).first()
        
        chat_room = None
        if not existing_room:
            # 사용자 정보 조회
            requester = db.query(User).filter(User.user_id == matching_request.requester_id).first()
            requested = db.query(User).filter(User.user_id == matching_request.requested_id).first()
            
            # 1:1 채팅방 생성
            chat_room = ChatRoom(
                room_name=f"{requester.name}, {requested.name}",
                room_type='direct',
                created_by=matching_request.requester_id
            )
            db.add(chat_room)
            db.flush()  # room_id 생성
            
            # 참여자 추가
            participant1 = ChatParticipant(
                room_id=chat_room.room_id,
                user_id=matching_request.requester_id,
                is_active=True
            )
            participant2 = ChatParticipant(
                room_id=chat_room.room_id,
                user_id=matching_request.requested_id,
                is_active=True
            )
            db.add(participant1)
            db.add(participant2)
        else:
            chat_room = existing_room
        
        db.commit()
        db.refresh(chat_room)
        
        return {
            "message": "매칭 요청이 수락되었습니다.",
            "chat_room_id": chat_room.room_id,
            "chat_room_name": chat_room.room_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="매칭 요청 수락 중 오류가 발생했습니다."
        )

@app.post("/matching/requests/{request_id}/reject/")
async def reject_matching_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """매칭 요청을 거절합니다."""
    try:
        matching_request = db.query(MatchingRequest).filter(
            MatchingRequest.request_id == request_id,
            MatchingRequest.requested_id == current_user.user_id,
            MatchingRequest.status == 'pending'
        ).first()
        
        if not matching_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="매칭 요청을 찾을 수 없습니다."
            )
        
        matching_request.status = 'rejected'
        db.commit()
        
        return {"message": "매칭 요청이 거절되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="매칭 요청 거절 중 오류가 발생했습니다."
        )

@app.get("/matching/requests/", response_model=MatchingRequestListResponse)
async def get_matching_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    type: str = "received"  # received, sent
):
    """매칭 요청 목록을 조회합니다."""
    try:
        if type == "received":
            requests = db.query(MatchingRequest).filter(
                MatchingRequest.requested_id == current_user.user_id,
                MatchingRequest.status == 'pending'
            ).all()
        else:
            requests = db.query(MatchingRequest).filter(
                MatchingRequest.requester_id == current_user.user_id
            ).all()
        
        results = []
        for req in requests:
            requester = db.query(User).filter(User.user_id == req.requester_id).first()
            requested = db.query(User).filter(User.user_id == req.requested_id).first()
            
            results.append(MatchingRequestResponse(
                request_id=req.request_id,
                requester_id=req.requester_id,
                requester_name=requester.name if requester else "알 수 없음",
                requested_id=req.requested_id,
                requested_name=requested.name if requested else "알 수 없음",
                status=req.status,
                created_at=req.created_at,
                updated_at=req.updated_at
            ))
        
        return MatchingRequestListResponse(requests=results, total_count=len(results))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="매칭 요청 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/matching/friends/", response_model=FriendListResponse)
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """친구 목록을 조회합니다."""
    try:
        friendships = db.query(FriendRelationship).filter(
            ((FriendRelationship.user1_id == current_user.user_id) |
             (FriendRelationship.user2_id == current_user.user_id)),
            FriendRelationship.is_active == True
        ).all()
        
        results = []
        for friendship in friendships:
            friend_id = friendship.user2_id if friendship.user1_id == current_user.user_id else friendship.user1_id
            friend = db.query(User).filter(User.user_id == friend_id).first()
            
            if friend:
                results.append(FriendResponse(
                    relationship_id=friendship.relationship_id,
                    friend_id=friend_id,
                    friend_name=friend.name,
                    created_at=friendship.created_at
                ))
        
        return FriendListResponse(friends=results, total_count=len(results))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="친구 목록 조회 중 오류가 발생했습니다."
        )

@app.delete("/matching/friends/{friend_id}/")
async def remove_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """친구 관계를 해제합니다."""
    try:
        friendship = db.query(FriendRelationship).filter(
            ((FriendRelationship.user1_id == current_user.user_id) & (FriendRelationship.user2_id == friend_id)) |
            ((FriendRelationship.user1_id == friend_id) & (FriendRelationship.user2_id == current_user.user_id)),
            FriendRelationship.is_active == True
        ).first()
        
        if not friendship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="친구 관계를 찾을 수 없습니다."
            )
        
        friendship.is_active = False
        db.commit()
        
        return {"message": "친구 관계가 해제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="친구 관계 해제 중 오류가 발생했습니다."
        )

# =============================================================================
# 게시판 API (그룹 내)
# =============================================================================

@app.post("/groups/{group_id}/posts/", response_model=GroupPostResponse, status_code=status.HTTP_201_CREATED)
async def create_group_post(
    group_id: int,
    post_data: GroupPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글을 생성합니다."""
    try:
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True,
            GroupMember.status == 'approved'
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 게시글을 작성할 수 있습니다."
            )
        
        post = GroupPost(
            group_id=group_id,
            author_id=current_user.user_id,
            title=post_data.title,
            content=post_data.content,
            category=post_data.category or "일반"
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        
        author = db.query(User).filter(User.user_id == post.author_id).first()
        comment_count = db.query(GroupPostComment).filter(
            GroupPostComment.post_id == post.post_id,
            GroupPostComment.is_deleted == False
        ).count()
        
        return GroupPostResponse(
            post_id=post.post_id,
            group_id=post.group_id,
            author_id=post.author_id,
            author_name=author.name if author else "알 수 없음",
            title=post.title,
            content=post.content,
            category=post.category or "일반",
            is_pinned=post.is_pinned,
            like_count=0,
            is_liked=False,
            created_at=post.created_at,
            updated_at=post.updated_at,
            comment_count=comment_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 생성 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/posts/", response_model=GroupPostListResponse)
async def get_group_posts(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 20
):
    """그룹 게시글 목록을 조회합니다."""
    try:
        posts = db.query(GroupPost).filter(
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False
        ).order_by(GroupPost.is_pinned.desc(), GroupPost.created_at.desc()).offset((page - 1) * size).limit(size).all()
        
        results = []
        for post in posts:
            author = db.query(User).filter(User.user_id == post.author_id).first()
            comment_count = db.query(GroupPostComment).filter(
                GroupPostComment.post_id == post.post_id,
                GroupPostComment.is_deleted == False
            ).count()
            
            like_count = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == post.post_id
            ).count()
            
            is_liked = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == post.post_id,
                GroupPostLike.user_id == current_user.user_id
            ).first() is not None
            
            results.append(GroupPostResponse(
                post_id=post.post_id,
                group_id=post.group_id,
                author_id=post.author_id,
                author_name=author.name if author else "알 수 없음",
                title=post.title,
                content=post.content,
                category=post.category or "일반",
                is_pinned=post.is_pinned,
                like_count=like_count,
                is_liked=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at,
                comment_count=comment_count
            ))
        
        return GroupPostListResponse(posts=results, total_count=len(results))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/posts/{post_id}", response_model=GroupPostResponse)
async def get_group_post(
    group_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글 상세를 조회합니다."""
    try:
        post = db.query(GroupPost).filter(
            GroupPost.post_id == post_id,
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        author = db.query(User).filter(User.user_id == post.author_id).first()
        comment_count = db.query(GroupPostComment).filter(
            GroupPostComment.post_id == post.post_id,
            GroupPostComment.is_deleted == False
        ).count()
        
        like_count = db.query(GroupPostLike).filter(
            GroupPostLike.post_id == post.post_id
        ).count()
        
        is_liked = db.query(GroupPostLike).filter(
            GroupPostLike.post_id == post.post_id,
            GroupPostLike.user_id == current_user.user_id
        ).first() is not None
        
        return GroupPostResponse(
            post_id=post.post_id,
            group_id=post.group_id,
            author_id=post.author_id,
            author_name=author.name if author else "알 수 없음",
            title=post.title,
            content=post.content,
            category=post.category or "일반",
            is_pinned=post.is_pinned,
            like_count=like_count,
            is_liked=is_liked,
            created_at=post.created_at,
            updated_at=post.updated_at,
            comment_count=comment_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 조회 중 오류가 발생했습니다."
        )

@app.put("/groups/{group_id}/posts/{post_id}", response_model=GroupPostResponse)
async def update_group_post(
    group_id: int,
    post_id: int,
    post_data: GroupPostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글을 수정합니다."""
    try:
        post = db.query(GroupPost).filter(
            GroupPost.post_id == post_id,
            GroupPost.group_id == group_id,
            GroupPost.author_id == current_user.user_id,
            GroupPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없거나 수정 권한이 없습니다."
            )
        
        if post_data.title is not None:
            post.title = post_data.title
        if post_data.content is not None:
            post.content = post_data.content
        if post_data.category is not None:
            post.category = post_data.category
        
        db.commit()
        db.refresh(post)
        
        author = db.query(User).filter(User.user_id == post.author_id).first()
        comment_count = db.query(GroupPostComment).filter(
            GroupPostComment.post_id == post.post_id,
            GroupPostComment.is_deleted == False
        ).count()
        
        like_count = db.query(GroupPostLike).filter(
            GroupPostLike.post_id == post.post_id
        ).count()
        
        is_liked = db.query(GroupPostLike).filter(
            GroupPostLike.post_id == post.post_id,
            GroupPostLike.user_id == current_user.user_id
        ).first() is not None
        
        return GroupPostResponse(
            post_id=post.post_id,
            group_id=post.group_id,
            author_id=post.author_id,
            author_name=author.name if author else "알 수 없음",
            title=post.title,
            content=post.content,
            category=post.category or "일반",
            is_pinned=post.is_pinned,
            like_count=like_count,
            is_liked=is_liked,
            created_at=post.created_at,
            updated_at=post.updated_at,
            comment_count=comment_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 수정 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/posts/{post_id}")
async def delete_group_post(
    group_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글을 삭제합니다."""
    try:
        post = db.query(GroupPost).filter(
            GroupPost.post_id == post_id,
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 작성자 또는 관리자만 삭제 가능
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if post.author_id != current_user.user_id and not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="게시글 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        post.is_deleted = True
        db.commit()
        
        return {"message": "게시글이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 삭제 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/posts/{post_id}/comments/", response_model=GroupPostCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_group_post_comment(
    group_id: int,
    post_id: int,
    comment_data: GroupPostCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글에 댓글을 작성합니다."""
    try:
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True,
            GroupMember.status == 'approved'
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 댓글을 작성할 수 있습니다."
            )
        
        comment = GroupPostComment(
            post_id=post_id,
            author_id=current_user.user_id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        author = db.query(User).filter(User.user_id == comment.author_id).first()
        
        return GroupPostCommentResponse(
            comment_id=comment.comment_id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_name=author.name if author else "알 수 없음",
            content=comment.content,
            parent_comment_id=comment.parent_comment_id,
            like_count=0,
            is_liked=False,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 생성 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/posts/{post_id}/comments/", response_model=GroupPostCommentListResponse)
async def get_group_post_comments(
    group_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글 댓글 목록을 조회합니다."""
    try:
        comments = db.query(GroupPostComment).filter(
            GroupPostComment.post_id == post_id,
            GroupPostComment.is_deleted == False
        ).order_by(GroupPostComment.created_at.asc()).all()
        
        results = []
        for comment in comments:
            author = db.query(User).filter(User.user_id == comment.author_id).first()
            
            # 좋아요 수 계산
            like_count = db.query(GroupPostCommentLike).filter(
                GroupPostCommentLike.comment_id == comment.comment_id
            ).count()
            
            is_liked = db.query(GroupPostCommentLike).filter(
                GroupPostCommentLike.comment_id == comment.comment_id,
                GroupPostCommentLike.user_id == current_user.user_id
            ).first() is not None
            
            results.append(GroupPostCommentResponse(
                comment_id=comment.comment_id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_name=author.name if author else "알 수 없음",
                content=comment.content,
                parent_comment_id=comment.parent_comment_id,
                like_count=like_count,
                is_liked=is_liked,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            ))
        
        return GroupPostCommentListResponse(comments=results, total_count=len(results))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 목록 조회 중 오류가 발생했습니다."
        )

@app.put("/groups/{group_id}/posts/{post_id}/comments/{comment_id}", response_model=GroupPostCommentResponse)
async def update_group_post_comment(
    group_id: int,
    post_id: int,
    comment_id: int,
    comment_data: GroupPostCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글 댓글을 수정합니다."""
    try:
        comment = db.query(GroupPostComment).filter(
            GroupPostComment.comment_id == comment_id,
            GroupPostComment.post_id == post_id,
            GroupPostComment.author_id == current_user.user_id,
            GroupPostComment.is_deleted == False
        ).first()
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="댓글을 찾을 수 없거나 수정 권한이 없습니다."
            )
        
        if comment_data.content is not None:
            comment.content = comment_data.content
        
        db.commit()
        db.refresh(comment)
        
        author = db.query(User).filter(User.user_id == comment.author_id).first()
        
        # 좋아요 수 계산
        like_count = db.query(GroupPostCommentLike).filter(
            GroupPostCommentLike.comment_id == comment.comment_id
        ).count()
        
        is_liked = db.query(GroupPostCommentLike).filter(
            GroupPostCommentLike.comment_id == comment.comment_id,
            GroupPostCommentLike.user_id == current_user.user_id
        ).first() is not None
        
        return GroupPostCommentResponse(
            comment_id=comment.comment_id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_name=author.name if author else "알 수 없음",
            content=comment.content,
            parent_comment_id=comment.parent_comment_id,
            like_count=like_count,
            is_liked=is_liked,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 수정 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/posts/{post_id}/comments/{comment_id}")
async def delete_group_post_comment(
    group_id: int,
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 게시글 댓글을 삭제합니다."""
    try:
        comment = db.query(GroupPostComment).filter(
            GroupPostComment.comment_id == comment_id,
            GroupPostComment.post_id == post_id,
            GroupPostComment.is_deleted == False
        ).first()
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="댓글을 찾을 수 없습니다."
            )
        
        # 작성자 또는 관리자만 삭제 가능
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if comment.author_id != current_user.user_id and not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="댓글 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        comment.is_deleted = True
        db.commit()
        
        return {"message": "댓글이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 삭제 중 오류가 발생했습니다."
        )

# =============================================================================
# 갤러리 시스템 API
# =============================================================================

@app.post("/groups/{group_id}/gallery/", response_model=GroupGalleryResponse, status_code=status.HTTP_201_CREATED)
async def upload_group_gallery_image(
    group_id: int,
    image: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 갤러리에 이미지를 업로드합니다."""
    try:
        
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            # 그룹 생성자인지 확인
            if group.created_by == current_user.user_id:
                # 생성자를 owner로 추가
                new_member = GroupMember(
                    group_id=group_id,
                    user_id=current_user.user_id,
                    role='owner',
                    is_active=True
                )
                db.add(new_member)
                db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="그룹 멤버만 이미지를 업로드할 수 있습니다."
                )
        
        # 파일 검증 (Content-Type 또는 파일 확장자로 확인)
        import os
        
        # 허용된 이미지 확장자
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        file_extension = os.path.splitext(image.filename)[1].lower() if image.filename else ''
        
        # Content-Type이 image/*이거나, 파일 확장자가 이미지 확장자인 경우 허용
        is_valid_content_type = image.content_type and image.content_type.startswith('image/')
        is_valid_extension = file_extension in allowed_extensions
        
        if not (is_valid_content_type or is_valid_extension):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이미지 파일만 업로드할 수 있습니다. (Content-Type: {image.content_type}, 확장자: {file_extension})"
            )
        
        
        # 파일 크기 검증 (10MB)
        content = await image.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일 크기는 10MB 이하여야 합니다."
            )
        
        # 파일 저장
        import os
        from datetime import datetime
        
        # 디렉토리 생성
        upload_dir = f"static/images/groups/{group_id}/gallery"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일명 생성 (타임스탬프 + 원본 파일명)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(image.filename)[1]
        file_name = f"{timestamp}_{current_user.user_id}{file_extension}"
        file_path = f"{upload_dir}/{file_name}"
        
        # 파일 저장
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 데이터베이스에 저장
        gallery_image = GroupGallery(
            group_id=group_id,
            uploaded_by=current_user.user_id,
            image_url=f"/{file_path}",
            file_name=image.filename,
            file_size=len(content),
            description=description
        )
        
        db.add(gallery_image)
        db.commit()
        db.refresh(gallery_image)
        
        return GroupGalleryResponse(
            image_id=gallery_image.image_id,
            group_id=gallery_image.group_id,
            uploaded_by=gallery_image.uploaded_by,
            uploader_name=current_user.name,
            image_url=gallery_image.image_url,
            file_name=gallery_image.file_name,
            file_size=gallery_image.file_size,
            description=gallery_image.description,
            created_at=gallery_image.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 업로드 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/gallery/", response_model=GroupGalleryListResponse)
async def get_group_gallery_images(
    group_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 갤러리 이미지 목록을 조회합니다."""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 비공개 그룹인 경우 멤버 확인
        if not group.is_public:
            member = db.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.user_id,
                GroupMember.is_active == True
            ).first()
            
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="그룹 멤버만 갤러리를 볼 수 있습니다."
                )
        
        # 갤러리 이미지 조회
        images_query = db.query(GroupGallery).filter(
            GroupGallery.group_id == group_id,
            GroupGallery.is_deleted == False
        ).order_by(GroupGallery.created_at.desc())
        
        total_count = images_query.count()
        images = images_query.offset(skip).limit(limit).all()
        
        # 업로더 정보 포함
        image_responses = []
        for img in images:
            uploader = db.query(User).filter(User.user_id == img.uploaded_by).first()
            image_responses.append(
                GroupGalleryResponse(
                    image_id=img.image_id,
                    group_id=img.group_id,
                    uploaded_by=img.uploaded_by,
                    uploader_name=uploader.name if uploader else "알 수 없음",
                    image_url=img.image_url,
                    file_name=img.file_name,
                    file_size=img.file_size,
                    description=img.description,
                    created_at=img.created_at
                )
            )
        
        return GroupGalleryListResponse(
            images=image_responses,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="갤러리 조회 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/gallery/{image_id}")
async def delete_group_gallery_image(
    group_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 갤러리 이미지를 삭제합니다."""
    try:
        # 이미지 조회
        image = db.query(GroupGallery).filter(
            GroupGallery.image_id == image_id,
            GroupGallery.group_id == group_id,
            GroupGallery.is_deleted == False
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 업로더 본인 또는 관리자만 삭제 가능
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if image.uploaded_by != current_user.user_id and not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이미지 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        image.is_deleted = True
        db.commit()
        
        # 실제 파일 삭제 (선택적)
        try:
            import os
            if os.path.exists(image.image_url.lstrip('/')):
                os.remove(image.image_url.lstrip('/'))
        except Exception:
            pass
        
        return {"message": "이미지가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 삭제 중 오류가 발생했습니다."
        )

# =============================================================================
# 그룹 멤버 관리 API
# =============================================================================

@app.put("/groups/{group_id}/members/{user_id}/role/", response_model=GroupMemberResponse)
async def update_group_member_role(
    group_id: int,
    user_id: int,
    role_update: GroupMemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 멤버의 역할을 변경합니다. (owner와 admin만 가능)"""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 현재 사용자 권한 확인 (owner 또는 admin)
        current_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if not current_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="멤버 역할을 변경할 권한이 없습니다. (owner 또는 admin만 가능)"
            )
        
        # 변경 대상 멤버 조회
        target_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.is_active == True
        ).first()
        
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹 멤버를 찾을 수 없습니다."
            )
        
        # owner는 변경할 수 없음
        if target_member.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 소유자의 역할은 변경할 수 없습니다."
            )
        
        # admin은 owner만 변경 가능
        if target_member.role == 'admin' and current_member.role != 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자의 역할은 소유자만 변경할 수 있습니다."
            )
        
        # owner로 변경은 불가
        if role_update.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소유자 역할로는 변경할 수 없습니다."
            )
        
        # 역할 변경
        target_member.role = role_update.role
        db.commit()
        db.refresh(target_member)
        
        # 사용자 정보 조회
        user = db.query(User).filter(User.user_id == user_id).first()
        
        return GroupMemberResponse(
            member_id=target_member.member_id,
            group_id=target_member.group_id,
            user_id=target_member.user_id,
            user_name=user.name if user else "알 수 없음",
            role=target_member.role,
            status=target_member.status,
            joined_at=target_member.joined_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="멤버 역할 변경 중 오류가 발생했습니다."
        )

# =============================================================================
# 정기모임 관리 API
# =============================================================================

@app.post("/groups/{group_id}/meetings/", response_model=GroupMeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_group_meeting(
    group_id: int,
    meeting_data: GroupMeetingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 정기모임을 생성합니다."""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 그룹 관리자 권한 확인 (owner 또는 admin)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="정기모임을 생성할 권한이 없습니다. (owner 또는 admin만 가능)"
            )
        
        # 정기모임 생성
        meeting = GroupMeeting(
            group_id=group_id,
            created_by=current_user.user_id,
            title=meeting_data.title,
            description=meeting_data.description,
            meeting_date=meeting_data.meeting_date,
            location=meeting_data.location,
            max_attendees=meeting_data.max_attendees
        )
        
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        return GroupMeetingResponse(
            meeting_id=meeting.meeting_id,
            group_id=meeting.group_id,
            created_by=meeting.created_by,
            creator_name=current_user.name,
            title=meeting.title,
            description=meeting.description,
            meeting_date=meeting.meeting_date,
            location=meeting.location,
            max_attendees=meeting.max_attendees,
            attendee_count=0,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="정기모임 생성 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/meetings/", response_model=GroupMeetingListResponse)
async def get_group_meetings(
    group_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 정기모임 목록을 조회합니다."""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 비공개 그룹인 경우 멤버 확인
        if not group.is_public:
            member = db.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.user_id,
                GroupMember.is_active == True
            ).first()
            
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="그룹 멤버만 정기모임을 볼 수 있습니다."
                )
        
        # 정기모임 조회 (최신순)
        meetings_query = db.query(GroupMeeting).filter(
            GroupMeeting.group_id == group_id,
            GroupMeeting.is_deleted == False
        ).order_by(GroupMeeting.meeting_date.desc())
        
        total_count = meetings_query.count()
        meetings = meetings_query.offset(skip).limit(limit).all()
        
        # 응답 생성
        meeting_responses = []
        for meeting in meetings:
            creator = db.query(User).filter(User.user_id == meeting.created_by).first()
            attendee_count = db.query(GroupMeetingAttendee).filter(
                GroupMeetingAttendee.meeting_id == meeting.meeting_id,
                GroupMeetingAttendee.status == 'attending'
            ).count()
            
            meeting_responses.append(
                GroupMeetingResponse(
                    meeting_id=meeting.meeting_id,
                    group_id=meeting.group_id,
                    created_by=meeting.created_by,
                    creator_name=creator.name if creator else "알 수 없음",
                    title=meeting.title,
                    description=meeting.description,
                    meeting_date=meeting.meeting_date,
                    location=meeting.location,
                    max_attendees=meeting.max_attendees,
                    attendee_count=attendee_count,
                    created_at=meeting.created_at,
                    updated_at=meeting.updated_at
                )
            )
        
        return GroupMeetingListResponse(
            meetings=meeting_responses,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="정기모임 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/meetings/{meeting_id}", response_model=GroupMeetingResponse)
async def get_group_meeting(
    group_id: int,
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 정기모임 상세 정보를 조회합니다."""
    try:
        # 정기모임 조회
        meeting = db.query(GroupMeeting).filter(
            GroupMeeting.meeting_id == meeting_id,
            GroupMeeting.group_id == group_id,
            GroupMeeting.is_deleted == False
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정기모임을 찾을 수 없습니다."
            )
        
        # 그룹 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        
        # 비공개 그룹인 경우 멤버 확인
        if not group.is_public:
            member = db.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.user_id,
                GroupMember.is_active == True
            ).first()
            
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="그룹 멤버만 정기모임을 볼 수 있습니다."
                )
        
        # 생성자 정보 조회
        creator = db.query(User).filter(User.user_id == meeting.created_by).first()
        
        # 참석자 수 조회
        attendee_count = db.query(GroupMeetingAttendee).filter(
            GroupMeetingAttendee.meeting_id == meeting_id,
            GroupMeetingAttendee.status == 'attending'
        ).count()
        
        return GroupMeetingResponse(
            meeting_id=meeting.meeting_id,
            group_id=meeting.group_id,
            created_by=meeting.created_by,
            creator_name=creator.name if creator else "알 수 없음",
            title=meeting.title,
            description=meeting.description,
            meeting_date=meeting.meeting_date,
            location=meeting.location,
            max_attendees=meeting.max_attendees,
            attendee_count=attendee_count,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="정기모임 상세 조회 중 오류가 발생했습니다."
        )

@app.put("/groups/{group_id}/meetings/{meeting_id}", response_model=GroupMeetingResponse)
async def update_group_meeting(
    group_id: int,
    meeting_id: int,
    meeting_data: GroupMeetingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 정기모임을 수정합니다."""
    try:
        # 정기모임 조회
        meeting = db.query(GroupMeeting).filter(
            GroupMeeting.meeting_id == meeting_id,
            GroupMeeting.group_id == group_id,
            GroupMeeting.is_deleted == False
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정기모임을 찾을 수 없습니다."
            )
        
        # 생성자 또는 관리자만 수정 가능
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if meeting.created_by != current_user.user_id and not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="정기모임을 수정할 권한이 없습니다."
            )
        
        # 필드 업데이트
        if meeting_data.title is not None:
            meeting.title = meeting_data.title
        if meeting_data.description is not None:
            meeting.description = meeting_data.description
        if meeting_data.meeting_date is not None:
            meeting.meeting_date = meeting_data.meeting_date
        if meeting_data.location is not None:
            meeting.location = meeting_data.location
        if meeting_data.max_attendees is not None:
            meeting.max_attendees = meeting_data.max_attendees
        
        db.commit()
        db.refresh(meeting)
        
        # 생성자 정보
        creator = db.query(User).filter(User.user_id == meeting.created_by).first()
        
        # 참석자 수
        attendee_count = db.query(GroupMeetingAttendee).filter(
            GroupMeetingAttendee.meeting_id == meeting_id,
            GroupMeetingAttendee.status == 'attending'
        ).count()
        
        return GroupMeetingResponse(
            meeting_id=meeting.meeting_id,
            group_id=meeting.group_id,
            created_by=meeting.created_by,
            creator_name=creator.name if creator else "알 수 없음",
            title=meeting.title,
            description=meeting.description,
            meeting_date=meeting.meeting_date,
            location=meeting.location,
            max_attendees=meeting.max_attendees,
            attendee_count=attendee_count,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="정기모임 수정 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/meetings/{meeting_id}")
async def delete_group_meeting(
    group_id: int,
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 정기모임을 삭제합니다."""
    try:
        # 정기모임 조회
        meeting = db.query(GroupMeeting).filter(
            GroupMeeting.meeting_id == meeting_id,
            GroupMeeting.group_id == group_id,
            GroupMeeting.is_deleted == False
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정기모임을 찾을 수 없습니다."
            )
        
        # 생성자 또는 관리자만 삭제 가능
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if meeting.created_by != current_user.user_id and not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="정기모임을 삭제할 권한이 없습니다."
            )
        
        # 소프트 삭제
        meeting.is_deleted = True
        db.commit()
        
        return {"message": "정기모임이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="정기모임 삭제 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/meetings/{meeting_id}/attend")
async def attend_group_meeting(
    group_id: int,
    meeting_id: int,
    attend_data: GroupMeetingAttendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """정기모임 참석 상태를 업데이트합니다 (attending/not_attending/maybe)."""
    try:
        # 정기모임 조회
        meeting = db.query(GroupMeeting).filter(
            GroupMeeting.meeting_id == meeting_id,
            GroupMeeting.group_id == group_id,
            GroupMeeting.is_deleted == False
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정기모임을 찾을 수 없습니다."
            )
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 참석 신청할 수 있습니다."
            )
        
        # 상태 검증
        if attend_data.status not in ['attending', 'not_attending', 'maybe']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="올바른 참석 상태가 아닙니다. (attending/not_attending/maybe)"
            )
        
        # 최대 참석자 수 확인 (attending으로 변경 시)
        if attend_data.status == 'attending' and meeting.max_attendees:
            current_attendee_count = db.query(GroupMeetingAttendee).filter(
                GroupMeetingAttendee.meeting_id == meeting_id,
                GroupMeetingAttendee.status == 'attending',
                GroupMeetingAttendee.user_id != current_user.user_id
            ).count()
            
            if current_attendee_count >= meeting.max_attendees:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="참석 인원이 마감되었습니다."
                )
        
        # 이미 참석 기록이 있는지 확인
        existing = db.query(GroupMeetingAttendee).filter(
            GroupMeetingAttendee.meeting_id == meeting_id,
            GroupMeetingAttendee.user_id == current_user.user_id
        ).first()
        
        if existing:
            # 상태 업데이트
            existing.status = attend_data.status
            db.commit()
        else:
            # 새로 생성
            attendee = GroupMeetingAttendee(
                meeting_id=meeting_id,
                user_id=current_user.user_id,
                status=attend_data.status
            )
            db.add(attendee)
            db.commit()
        
        # 참석자 수 계산 (attending만)
        attendee_count = db.query(GroupMeetingAttendee).filter(
            GroupMeetingAttendee.meeting_id == meeting_id,
            GroupMeetingAttendee.status == 'attending'
        ).count()
        
        status_message = {
            'attending': '참석 신청이 완료되었습니다.',
            'not_attending': '불참 처리되었습니다.',
            'maybe': '미정으로 처리되었습니다.'
        }
        
        return {
            "message": status_message.get(attend_data.status, "상태가 업데이트되었습니다."),
            "status": attend_data.status,
            "attendee_count": attendee_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="참석 신청 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/meetings/{meeting_id}/attend")
async def cancel_attend_group_meeting(
    group_id: int,
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """정기모임 참석을 취소합니다."""
    try:
        # 참석 정보 조회
        attendee = db.query(GroupMeetingAttendee).filter(
            GroupMeetingAttendee.meeting_id == meeting_id,
            GroupMeetingAttendee.user_id == current_user.user_id
        ).first()
        
        if not attendee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="참석 정보를 찾을 수 없습니다."
            )
        
        # 상태 변경 (삭제하지 않고 not_attending으로 변경)
        attendee.status = 'not_attending'
        db.commit()
        
        return {"message": "참석이 취소되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="참석 취소 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/meetings/{meeting_id}/attendees")
async def get_meeting_attendees(
    group_id: int,
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """정기모임 참석자 목록을 조회합니다."""
    try:
        # 정기모임 조회
        meeting = db.query(GroupMeeting).filter(
            GroupMeeting.meeting_id == meeting_id,
            GroupMeeting.group_id == group_id,
            GroupMeeting.is_deleted == False
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정기모임을 찾을 수 없습니다."
            )
        
        # 그룹 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        
        # 비공개 그룹인 경우 멤버 확인
        if not group.is_public:
            member = db.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.user_id,
                GroupMember.is_active == True
            ).first()
            
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="그룹 멤버만 참석자 목록을 볼 수 있습니다."
                )
        
        # 참석자 목록 조회 (참석 확정만)
        attendees = db.query(GroupMeetingAttendee).filter(
            GroupMeetingAttendee.meeting_id == meeting_id,
            GroupMeetingAttendee.status == 'attending'
        ).all()
        
        # 사용자 정보 포함
        attendee_list = []
        for attendee in attendees:
            user = db.query(User).filter(User.user_id == attendee.user_id).first()
            if user:
                attendee_list.append({
                    "user_id": user.user_id,
                    "user_name": user.name,
                    "email": user.email,
                    "status": attendee.status,
                    "joined_at": attendee.created_at
                })
        
        return {
            "attendees": attendee_list,
            "total_count": len(attendee_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="참석자 목록 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# Phase 1: 그룹 좋아요/조회수/카테고리 시스템
# =============================================================================

@app.post("/groups/{group_id}/like/", response_model=GroupLikeResponse)
async def toggle_group_like(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 좋아요 추가/취소 (토글)"""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 기존 좋아요 확인
        existing_like = db.query(GroupLike).filter(
            GroupLike.group_id == group_id,
            GroupLike.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            # 좋아요 취소
            db.delete(existing_like)
            db.commit()
            is_liked = False
        else:
            # 좋아요 추가
            new_like = GroupLike(
                group_id=group_id,
                user_id=current_user.user_id
            )
            db.add(new_like)
            db.commit()
            is_liked = True
        
        # 좋아요 수 조회
        like_count = db.query(GroupLike).filter(GroupLike.group_id == group_id).count()
        
        return GroupLikeResponse(
            group_id=group_id,
            like_count=like_count,
            is_liked=is_liked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 처리 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/likes/", response_model=GroupLikeResponse)
async def get_group_likes(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 좋아요 수 및 상태 조회"""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 좋아요 수 조회
        like_count = db.query(GroupLike).filter(GroupLike.group_id == group_id).count()
        
        # 현재 사용자 좋아요 여부 확인
        is_liked = db.query(GroupLike).filter(
            GroupLike.group_id == group_id,
            GroupLike.user_id == current_user.user_id
        ).first() is not None
        
        return GroupLikeResponse(
            group_id=group_id,
            like_count=like_count,
            is_liked=is_liked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 정보 조회 중 오류가 발생했습니다."
        )

def weekdays_to_korean(weekdays: Optional[List[int]]) -> Optional[str]:
    """요일 숫자 리스트를 한글로 변환 (예: [2, 7] -> "화,일")"""
    if not weekdays:
        return None
    
    weekday_map = {
        1: "월", 2: "화", 3: "수", 4: "목", 5: "금", 6: "토", 7: "일"
    }
    
    korean_days = [weekday_map.get(day, "") for day in weekdays if day in weekday_map]
    return ",".join(korean_days) if korean_days else None

@app.get("/groups/categories/", response_model=GroupCategoryListResponse)
async def get_group_categories():
    """그룹 카테고리 목록 조회"""
    return GroupCategoryListResponse(
        categories=[category.value for category in GroupCategoryEnum]
    )

@app.get("/groups/{group_id}/stats/", response_model=GroupStatsResponse)
async def get_group_stats(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모임 통계 조회"""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 멤버 권한 확인 (멤버만 통계 조회 가능)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member and group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 통계를 조회할 수 있습니다."
            )
        
        # 총 멤버 수
        total_members = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True,
            GroupMember.role != 'pending'
        ).count()
        
        # 주간 활성 멤버 수 (최근 7일 내 게시글/댓글 작성자)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        
        active_post_users = db.query(GroupPost.author_id).filter(
            GroupPost.group_id == group_id,
            GroupPost.created_at >= week_ago
        ).distinct().count()
        
        active_comment_users = db.query(GroupPostComment.author_id).filter(
            GroupPostComment.post_id.in_(
                db.query(GroupPost.post_id).filter(GroupPost.group_id == group_id)
            ),
            GroupPostComment.created_at >= week_ago
        ).distinct().count()
        
        active_members_week = max(active_post_users, active_comment_users)
        
        # 주간 신규 멤버 수
        new_members_week = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.joined_at >= week_ago,
            GroupMember.is_active == True
        ).count()
        
        # 총 게시글 수
        total_posts = db.query(GroupPost).filter(
            GroupPost.group_id == group_id
        ).count()
        
        # 총 댓글 수
        total_comments = db.query(GroupPostComment).filter(
            GroupPostComment.post_id.in_(
                db.query(GroupPost.post_id).filter(GroupPost.group_id == group_id)
            )
        ).count()
        
        # 총 모임 수
        total_meetings = db.query(GroupMeeting).filter(
            GroupMeeting.group_id == group_id
        ).count()
        
        # 총 좋아요 수
        total_likes = db.query(GroupLike).filter(
            GroupLike.group_id == group_id
        ).count()
        
        return GroupStatsResponse(
            group_id=group_id,
            total_members=total_members,
            active_members_week=active_members_week,
            new_members_week=new_members_week,
            total_posts=total_posts,
            total_comments=total_comments,
            total_meetings=total_meetings,
            total_likes=total_likes,
            view_count=group.view_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/groups/{group_id}/stats/member-growth/", response_model=MemberGrowthResponse)
async def get_member_growth_stats(
    group_id: int,
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """멤버 성장 현황 조회 (최근 N개월)"""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 멤버 권한 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member and group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 통계를 조회할 수 있습니다."
            )
        
        from datetime import datetime, timedelta
        from calendar import monthrange
        
        # 월별 멤버 수 계산
        growth_data = []
        current_date = datetime.now()
        
        for i in range(months):
            # N개월 전 계산
            year = current_date.year
            month = current_date.month - i
            
            # 음수 월 처리
            while month <= 0:
                month += 12
                year -= 1
            
            month_str = f"{year:04d}-{month:02d}"
            
            # 해당 월의 마지막 날 계산
            last_day = monthrange(year, month)[1]
            month_end = datetime(year, month, last_day, 23, 59, 59)
            
            # 해당 월까지 가입한 멤버 수
            member_count = db.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.joined_at <= month_end,
                GroupMember.is_active == True
            ).count()
            
            growth_data.insert(0, MemberGrowthData(
                month=month_str,
                member_count=member_count
            ))
        
        return MemberGrowthResponse(
            group_id=group_id,
            data=growth_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/groups/{group_id}/posts/stats/by-category/", response_model=PostCategoryStatsResponse)
async def get_post_category_stats(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """카테고리별 게시글 통계 조회"""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 멤버 권한 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member and group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 통계를 조회할 수 있습니다."
            )
        
        from sqlalchemy import func
        
        # 카테고리별 게시글 수 집계
        category_stats = db.query(
            GroupPost.category,
            func.count(GroupPost.post_id).label('count')
        ).filter(
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False
        ).group_by(
            GroupPost.category
        ).all()
        
        stats = [
            PostCategoryStats(
                category=category or "일반",
                count=count
            )
            for category, count in category_stats
        ]
        
        # 카테고리가 없으면 기본값 반환
        if not stats:
            stats = [PostCategoryStats(category="일반", count=0)]
        
        return PostCategoryStatsResponse(
            group_id=group_id,
            stats=stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/users/{user_id}/groups/", response_model=GroupListResponse)
async def get_user_groups(
    user_id: int,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자가 가입한 모임 목록 조회"""
    try:
        # 권한 확인 (본인만 조회 가능)
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 모임 목록만 조회할 수 있습니다."
            )
        
        # 사용자가 멤버로 있는 그룹 조회
        query = db.query(Group).join(GroupMember).filter(
            GroupMember.user_id == user_id,
            GroupMember.is_active == True,
            GroupMember.role != 'pending',  # 대기 중인 신청은 제외
            Group.is_active == True
        )
        
        # 전체 개수
        total_count = query.count()
        
        # 페이지네이션
        offset = (page - 1) * size
        groups = query.order_by(Group.created_at.desc()).offset(offset).limit(size).all()
        
        # GroupResponse로 변환
        group_responses = []
        for group in groups:
            member_count = db.query(GroupMember).filter(
                GroupMember.group_id == group.group_id,
                GroupMember.is_active == True
            ).count()
            
            like_count = db.query(GroupLike).filter(
                GroupLike.group_id == group.group_id
            ).count()
            
            is_liked = db.query(GroupLike).filter(
                GroupLike.group_id == group.group_id,
                GroupLike.user_id == current_user.user_id
            ).first() is not None
            
            pending_requests = db.query(GroupMember).filter(
                GroupMember.group_id == group.group_id,
                GroupMember.role == 'pending'
            ).count()
            
            creator = db.query(User).filter(User.user_id == group.created_by).first()
            
            # tags를 JSON에서 리스트로 변환
            tags_list = []
            if group.tags:
                try:
                    tags_list = json.loads(group.tags) if isinstance(group.tags, str) else group.tags
                except:
                    tags_list = []
            
            # regular_weekday를 JSON에서 리스트로 변환
            weekday_list = []
            if group.regular_weekday:
                try:
                    weekday_list = json.loads(group.regular_weekday) if isinstance(group.regular_weekday, str) else group.regular_weekday
                except:
                    weekday_list = []
            
            # 한글 요일 표시 생성
            weekday_display = weekdays_to_korean(weekday_list)
            
            # rules를 JSON에서 리스트로 변환
            rules_list = []
            if group.rules:
                try:
                    rules_list = json.loads(group.rules) if isinstance(group.rules, str) else group.rules
                except:
                    rules_list = []
            
            # activity_plan을 JSON에서 리스트로 변환
            activity_plan_list = []
            if group.activity_plan:
                try:
                    activity_plan_list = json.loads(group.activity_plan) if isinstance(group.activity_plan, str) else group.activity_plan
                except:
                    activity_plan_list = []
            
            group_responses.append(GroupResponse(
                group_id=group.group_id,
                group_name=group.group_name,
                description=group.description,
                is_public=group.is_public,
                requires_approval=group.requires_approval,
                max_members=group.max_members,
                category=group.category,
                tags=tags_list,
                primary_image_url=group.primary_image_url,
                is_regular=group.is_regular,
                regular_weekday=weekday_list,
                regular_weekday_display=weekday_display,
                regular_time=group.regular_time,
                regular_location=group.regular_location,
                rules=rules_list,
                activity_plan=activity_plan_list,
                created_by=group.created_by,
                creator_name=creator.name if creator else "Unknown",
                is_active=group.is_active,
                member_count=member_count,
                like_count=like_count,
                is_liked=is_liked,
                view_count=group.view_count,
                pending_requests=pending_requests,
                created_at=group.created_at,
                updated_at=group.updated_at
            ))
        
        
        return GroupListResponse(
            groups=group_responses,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모임 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/groups/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 생성 (이미지 포함)"""
    try:
        # tags를 JSON 문자열로 변환
        tags_json = None
        if group_data.tags:
            tags_json = json.dumps(group_data.tags, ensure_ascii=False)
        
        # regular_weekday를 JSON 문자열로 변환 (List[int] -> JSON)
        weekday_json = None
        if group_data.regular_weekday:
            weekday_json = json.dumps(group_data.regular_weekday)
        
        # rules를 JSON 문자열로 변환
        rules_json = None
        if group_data.rules:
            rules_json = json.dumps(group_data.rules, ensure_ascii=False)
        
        # activity_plan을 JSON 문자열로 변환
        activity_plan_json = None
        if group_data.activity_plan:
            activity_plan_json = json.dumps(group_data.activity_plan, ensure_ascii=False)
        
        # 새 그룹 생성
        new_group = Group(
            group_name=group_data.group_name,
            description=group_data.description,
            created_by=current_user.user_id,
            is_public=group_data.is_public,
            requires_approval=group_data.requires_approval,
            max_members=group_data.max_members,
            category=group_data.category,
            tags=tags_json,
            primary_image_url=group_data.primary_image_url,
            is_regular=group_data.is_regular,
            regular_weekday=weekday_json,
            regular_time=group_data.regular_time,
            regular_location=group_data.regular_location,
            rules=rules_json,
            activity_plan=activity_plan_json,
            view_count=0
        )
        
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        # 생성자를 owner로 자동 추가
        creator_member = GroupMember(
            group_id=new_group.group_id,
            user_id=current_user.user_id,
            role='owner',
            is_active=True
        )
        db.add(creator_member)
        db.commit()
        
        # 생성자 정보
        creator = db.query(User).filter(User.user_id == current_user.user_id).first()
        
        # tags를 다시 리스트로 변환
        tags_list = []
        if new_group.tags:
            try:
                tags_list = json.loads(new_group.tags)
            except:
                tags_list = []
        
        # regular_weekday를 JSON에서 리스트로 변환
        weekday_list = []
        if new_group.regular_weekday:
            try:
                weekday_list = json.loads(new_group.regular_weekday)
            except:
                weekday_list = []
        
        # rules를 JSON에서 리스트로 변환
        rules_list = []
        if new_group.rules:
            try:
                rules_list = json.loads(new_group.rules)
            except:
                rules_list = []
        
        # activity_plan을 JSON에서 리스트로 변환
        activity_plan_list = []
        if new_group.activity_plan:
            try:
                activity_plan_list = json.loads(new_group.activity_plan)
            except:
                activity_plan_list = []
        
        # 한글 요일 표시 생성
        weekday_display = weekdays_to_korean(weekday_list)
        
        return GroupResponse(
            group_id=new_group.group_id,
            group_name=new_group.group_name,
            description=new_group.description,
            is_public=new_group.is_public,
            requires_approval=new_group.requires_approval,
            max_members=new_group.max_members,
            category=new_group.category,
            tags=tags_list,
            primary_image_url=new_group.primary_image_url,
            is_regular=new_group.is_regular,
            regular_weekday=weekday_list,
            regular_weekday_display=weekday_display,
            regular_time=new_group.regular_time,
            regular_location=new_group.regular_location,
            rules=rules_list,
            activity_plan=activity_plan_list,
            created_by=new_group.created_by,
            creator_name=creator.name if creator else "Unknown",
            is_active=new_group.is_active,
            member_count=1,
            like_count=0,
            is_liked=False,
            view_count=0,
            pending_requests=0,
            created_at=new_group.created_at,
            updated_at=new_group.updated_at
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"그룹 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/groups/", response_model=GroupListResponse)
async def get_groups(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 목록 조회 (공개 그룹 + 내가 만든 그룹)"""
    try:
        # 공개 그룹 또는 내가 만든 그룹
        query = db.query(Group).filter(
            ((Group.is_public == True) | (Group.created_by == current_user.user_id)),
            Group.is_active == True
        )
        
        # 전체 개수
        total_count = query.count()
        
        # 페이지네이션
        offset = (page - 1) * size
        groups = query.order_by(Group.created_at.desc()).offset(offset).limit(size).all()
        
        # GroupResponse로 변환
        group_responses = []
        for group in groups:
            member_count = db.query(GroupMember).filter(
                GroupMember.group_id == group.group_id,
                GroupMember.is_active == True
            ).count()
            
            like_count = db.query(GroupLike).filter(
                GroupLike.group_id == group.group_id
            ).count()
            
            is_liked = db.query(GroupLike).filter(
                GroupLike.group_id == group.group_id,
                GroupLike.user_id == current_user.user_id
            ).first() is not None
            
            pending_requests = db.query(GroupMember).filter(
                GroupMember.group_id == group.group_id,
                GroupMember.role == 'pending'
            ).count()
            
            creator = db.query(User).filter(User.user_id == group.created_by).first()
            
            # tags를 JSON에서 리스트로 변환
            tags_list = []
            if group.tags:
                try:
                    tags_list = json.loads(group.tags) if isinstance(group.tags, str) else group.tags
                except:
                    tags_list = []
            
            # regular_weekday를 JSON에서 리스트로 변환
            weekday_list = []
            if group.regular_weekday:
                try:
                    weekday_list = json.loads(group.regular_weekday) if isinstance(group.regular_weekday, str) else group.regular_weekday
                except:
                    weekday_list = []
            
            # 한글 요일 표시 생성
            weekday_display = weekdays_to_korean(weekday_list)
            
            # rules를 JSON에서 리스트로 변환
            rules_list = []
            if group.rules:
                try:
                    rules_list = json.loads(group.rules) if isinstance(group.rules, str) else group.rules
                except:
                    rules_list = []
            
            # activity_plan을 JSON에서 리스트로 변환
            activity_plan_list = []
            if group.activity_plan:
                try:
                    activity_plan_list = json.loads(group.activity_plan) if isinstance(group.activity_plan, str) else group.activity_plan
                except:
                    activity_plan_list = []
            
            group_responses.append(GroupResponse(
                group_id=group.group_id,
                group_name=group.group_name,
                description=group.description,
                is_public=group.is_public,
                requires_approval=group.requires_approval,
                max_members=group.max_members,
                category=group.category,
                tags=tags_list,
                primary_image_url=group.primary_image_url,
                is_regular=group.is_regular,
                regular_weekday=weekday_list,
                regular_weekday_display=weekday_display,
                regular_time=group.regular_time,
                regular_location=group.regular_location,
                rules=rules_list,
                activity_plan=activity_plan_list,
                created_by=group.created_by,
                creator_name=creator.name if creator else "Unknown",
                is_active=group.is_active,
                member_count=member_count,
                like_count=like_count,
                is_liked=is_liked,
                view_count=group.view_count,
                pending_requests=pending_requests,
                created_at=group.created_at,
                updated_at=group.updated_at
            ))
        
        return GroupListResponse(
            groups=group_responses,
            total_count=total_count
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"그룹 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group_detail(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 상세 조회 (조회수 자동 증가)"""
    try:
        # 그룹 조회
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 조회수 증가
        group.view_count += 1
        db.commit()
        
        # 멤버 수 계산
        member_count = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        ).count()
        
        # 좋아요 수 계산
        like_count = db.query(GroupLike).filter(
            GroupLike.group_id == group_id
        ).count()
        
        # 현재 사용자 좋아요 여부
        is_liked = db.query(GroupLike).filter(
            GroupLike.group_id == group_id,
            GroupLike.user_id == current_user.user_id
        ).first() is not None
        
        # 가입 신청 대기 수
        pending_requests = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.role == 'pending'
        ).count()
        
        # 생성자 정보
        creator = db.query(User).filter(User.user_id == group.created_by).first()
        
        # tags를 JSON에서 리스트로 변환
        tags_list = []
        if group.tags:
            try:
                tags_list = json.loads(group.tags) if isinstance(group.tags, str) else group.tags
            except:
                tags_list = []
        
        # rules를 JSON에서 리스트로 변환
        rules_list = []
        if group.rules:
            try:
                rules_list = json.loads(group.rules) if isinstance(group.rules, str) else group.rules
            except:
                rules_list = []
        
        # activity_plan을 JSON에서 리스트로 변환
        activity_plan_list = []
        if group.activity_plan:
            try:
                activity_plan_list = json.loads(group.activity_plan) if isinstance(group.activity_plan, str) else group.activity_plan
            except:
                activity_plan_list = []
        
        # regular_weekday를 JSON에서 리스트로 변환
        regular_weekday_list = None
        regular_weekday_display = None
        if group.regular_weekday:
            try:
                if isinstance(group.regular_weekday, str):
                    regular_weekday_list = json.loads(group.regular_weekday)
                else:
                    regular_weekday_list = group.regular_weekday
                # 한글 요일 생성
                regular_weekday_display = weekdays_to_korean(regular_weekday_list)
            except:
                regular_weekday_list = None
        
        return GroupResponse(
            group_id=group.group_id,
            group_name=group.group_name,
            description=group.description,
            is_public=group.is_public,
            requires_approval=group.requires_approval,
            max_members=group.max_members,
            category=group.category,
            tags=tags_list,
            primary_image_url=group.primary_image_url,
            is_regular=group.is_regular,
            regular_weekday=regular_weekday_list,
            regular_weekday_display=regular_weekday_display,
            regular_time=str(group.regular_time) if group.regular_time else None,
            regular_location=group.regular_location,
            rules=rules_list,
            activity_plan=activity_plan_list,
            created_by=group.created_by,
            creator_name=creator.name if creator else "Unknown",
            is_active=group.is_active,
            member_count=member_count,
            like_count=like_count,
            is_liked=is_liked,
            view_count=group.view_count,
            pending_requests=pending_requests,
            created_at=group.created_at,
            updated_at=group.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="그룹 조회 중 오류가 발생했습니다."
        )

@app.get("/groups/search/", response_model=GroupListResponse)
async def search_groups(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 검색 (키워드, 카테고리, 태그)"""
    try:
        query = db.query(Group).filter(Group.is_active == True)
        
        # 키워드 검색
        if q:
            query = query.filter(
                (Group.group_name.like(f"%{q}%")) |
                (Group.description.like(f"%{q}%"))
            )
        
        # 카테고리 필터
        if category:
            query = query.filter(Group.category == category)
        
        # 태그 필터
        if tag:
            query = query.filter(Group.tags.like(f"%{tag}%"))
        
        # 전체 개수
        total_count = query.count()
        
        # 페이지네이션
        offset = (page - 1) * size
        groups = query.order_by(Group.created_at.desc()).offset(offset).limit(size).all()
        
        # GroupResponse로 변환
        group_responses = []
        for group in groups:
            member_count = db.query(GroupMember).filter(
                GroupMember.group_id == group.group_id,
                GroupMember.is_active == True
            ).count()
            
            like_count = db.query(GroupLike).filter(
                GroupLike.group_id == group.group_id
            ).count()
            
            is_liked = db.query(GroupLike).filter(
                GroupLike.group_id == group.group_id,
                GroupLike.user_id == current_user.user_id
            ).first() is not None
            
            creator = db.query(User).filter(User.user_id == group.created_by).first()
            
            tags_list = []
            if group.tags:
                try:
                    tags_list = json.loads(group.tags) if isinstance(group.tags, str) else group.tags
                except:
                    tags_list = []
            
            # rules를 JSON에서 리스트로 변환
            rules_list = []
            if group.rules:
                try:
                    rules_list = json.loads(group.rules) if isinstance(group.rules, str) else group.rules
                except:
                    rules_list = []
            
            # activity_plan을 JSON에서 리스트로 변환
            activity_plan_list = []
            if group.activity_plan:
                try:
                    activity_plan_list = json.loads(group.activity_plan) if isinstance(group.activity_plan, str) else group.activity_plan
                except:
                    activity_plan_list = []
            
            # regular_weekday를 JSON에서 리스트로 변환
            weekday_list = []
            if group.regular_weekday:
                try:
                    weekday_list = json.loads(group.regular_weekday) if isinstance(group.regular_weekday, str) else group.regular_weekday
                except:
                    weekday_list = []
            
            group_responses.append(GroupResponse(
                group_id=group.group_id,
                group_name=group.group_name,
                description=group.description,
                is_public=group.is_public,
                requires_approval=group.requires_approval,
                max_members=group.max_members,
                category=group.category,
                tags=tags_list,
                primary_image_url=group.primary_image_url,
                is_regular=group.is_regular,
                regular_weekday=weekday_list,
                regular_time=group.regular_time,
                regular_location=group.regular_location,
                rules=rules_list,
                activity_plan=activity_plan_list,
                created_by=group.created_by,
                creator_name=creator.name if creator else "Unknown",
                is_active=group.is_active,
                member_count=member_count,
                like_count=like_count,
                is_liked=is_liked,
                view_count=group.view_count,
                pending_requests=0,
                created_at=group.created_at,
                updated_at=group.updated_at
            ))
        
        return GroupListResponse(
            groups=group_responses,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="그룹 검색 중 오류가 발생했습니다."
        )

# =============================================================================
# Phase 1: 멤버 관리 (가입 신청/승인/거절)
# =============================================================================

@app.post("/groups/{group_id}/join-request/")
async def request_join_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 가입 신청"""
    try:
        # 그룹 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 이미 멤버인지 확인
        existing_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id
        ).first()
        
        if existing_member:
            if existing_member.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 그룹 멤버입니다."
                )
            elif existing_member.role == 'pending':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 가입 신청이 대기 중입니다."
                )
        
        # 최대 멤버 수 확인
        if group.max_members:
            current_members = db.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.is_active == True
            ).count()
            
            if current_members >= group.max_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="그룹이 최대 인원에 도달했습니다."
                )
        
        # 가입 신청 또는 즉시 가입
        if group.requires_approval:
            # 승인 필요 - pending 상태로 추가
            new_member = GroupMember(
                group_id=group_id,
                user_id=current_user.user_id,
                role='pending',
                is_active=False
            )
            message = "가입 신청이 완료되었습니다. 관리자 승인을 기다려주세요."
        else:
            # 승인 불필요 - 즉시 가입
            new_member = GroupMember(
                group_id=group_id,
                user_id=current_user.user_id,
                role='member',
                is_active=True
            )
            message = "그룹에 가입되었습니다!"
        
        db.add(new_member)
        db.commit()
        
        
        return {
            "message": message,
            "requires_approval": group.requires_approval,
            "status": new_member.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="가입 신청 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/join-requests/")
async def get_join_requests(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """가입 신청 대기 목록 조회 (관리자 전용)"""
    try:
        # 그룹 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 권한 확인 (그룹 생성자 또는 관리자만)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        is_creator = group.created_by == current_user.user_id
        is_admin = member and member.role in ['owner', 'admin']
        
        if not (is_creator or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자만 가입 신청 목록을 볼 수 있습니다."
            )
        
        # 대기 중인 신청 조회
        pending_requests = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.role == 'pending'
        ).all()
        
        # 사용자 정보 포함
        request_list = []
        for request in pending_requests:
            user = db.query(User).filter(User.user_id == request.user_id).first()
            if user:
                request_list.append({
                    "member_id": request.member_id,
                    "user_id": user.user_id,
                    "user_name": user.name,
                    "email": user.email,
                    "requested_at": request.joined_at
                })
        
        return {
            "requests": request_list,
            "total_count": len(request_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="가입 신청 목록 조회 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/approve/{user_id}/")
async def approve_join_request(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """가입 신청 승인 (관리자 전용)"""
    try:
        # 그룹 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 권한 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        is_creator = group.created_by == current_user.user_id
        is_admin = member and member.role in ['owner', 'admin']
        
        if not (is_creator or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자만 가입을 승인할 수 있습니다."
            )
        
        # 대기 중인 신청 찾기
        pending_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.role == 'pending'
        ).first()
        
        if not pending_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 가입 신청을 찾을 수 없습니다."
            )
        
        # 승인 처리
        pending_member.role = 'member'
        pending_member.is_active = True
        db.commit()
        
        
        return {
            "message": "가입이 승인되었습니다.",
            "user_id": user_id,
            "group_id": group_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="가입 승인 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/reject/{user_id}/")
async def reject_join_request(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """가입 신청 거절 (관리자 전용)"""
    try:
        # 그룹 확인
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 권한 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        is_creator = group.created_by == current_user.user_id
        is_admin = member and member.role in ['owner', 'admin']
        
        if not (is_creator or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자만 가입을 거절할 수 있습니다."
            )
        
        # 대기 중인 신청 찾기
        pending_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.role == 'pending'
        ).first()
        
        if not pending_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 가입 신청을 찾을 수 없습니다."
            )
        
        # 거절 처리 (삭제)
        db.delete(pending_member)
        db.commit()
        
        
        return {
            "message": "가입이 거절되었습니다.",
            "user_id": user_id,
            "group_id": group_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="가입 거절 중 오류가 발생했습니다."
        )

# =============================================================================
# 그룹 이벤트 API (Group Events)
# =============================================================================

@app.post("/groups/{group_id}/events/", response_model=GroupEventResponse, status_code=status.HTTP_201_CREATED)
async def create_group_event(
    group_id: int,
    event_data: GroupEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 이벤트를 생성합니다."""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 그룹 멤버 권한 확인 (owner 또는 admin)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이벤트 생성 권한이 없습니다."
            )
        
        # 이벤트 생성
        new_event = GroupEvent(
            group_id=group_id,
            title=event_data.title,
            description=event_data.description,
            event_date=event_data.event_date,
            event_time=event_data.event_time,
            location=event_data.location,
            max_attendees=event_data.max_attendees,
            is_mandatory=event_data.is_mandatory,
            created_by=current_user.user_id
        )
        
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        
        # 참석자 수 계산
        attendee_count = db.query(GroupEventAttendance).filter(
            GroupEventAttendance.event_id == new_event.event_id
        ).count()
        
        return GroupEventResponse(
            event_id=new_event.event_id,
            group_id=new_event.group_id,
            title=new_event.title,
            description=new_event.description,
            event_date=new_event.event_date,
            event_time=new_event.event_time,
            location=new_event.location,
            max_attendees=new_event.max_attendees,
            is_mandatory=new_event.is_mandatory,
            created_by=new_event.created_by,
            creator_name=current_user.name,
            attendee_count=attendee_count,
            my_attendance=None,
            created_at=new_event.created_at,
            updated_at=new_event.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이벤트 생성 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/events/", response_model=GroupEventListResponse)
async def get_group_events(
    group_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 이벤트 목록을 조회합니다."""
    try:
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 이벤트를 조회할 수 있습니다."
            )
        
        # 이벤트 조회
        query = db.query(GroupEvent).filter(
            GroupEvent.group_id == group_id,
            GroupEvent.is_deleted == False
        )
        
        # 날짜 필터
        if start_date:
            from datetime import datetime
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(GroupEvent.event_date >= start)
        if end_date:
            from datetime import datetime
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(GroupEvent.event_date <= end)
        
        # 전체 개수
        total_count = query.count()
        
        # 페이지네이션
        offset = (page - 1) * size
        events = query.order_by(GroupEvent.event_date.asc()).offset(offset).limit(size).all()
        
        # 응답 생성
        events_response = []
        for event in events:
            # 참석자 수
            attendee_count = db.query(GroupEventAttendance).filter(
                GroupEventAttendance.event_id == event.event_id
            ).count()
            
            # 내 참석 상태
            my_attendance_record = db.query(GroupEventAttendance).filter(
                GroupEventAttendance.event_id == event.event_id,
                GroupEventAttendance.user_id == current_user.user_id
            ).first()
            
            my_attendance = my_attendance_record.status if my_attendance_record else None
            
            # 생성자 이름
            creator = db.query(User).filter(User.user_id == event.created_by).first()
            creator_name = creator.name if creator else "알 수 없음"
            
            events_response.append(GroupEventResponse(
                event_id=event.event_id,
                group_id=event.group_id,
                title=event.title,
                description=event.description,
                event_date=event.event_date,
                event_time=event.event_time,
                location=event.location,
                max_attendees=event.max_attendees,
                is_mandatory=event.is_mandatory,
                created_by=event.created_by,
                creator_name=creator_name,
                attendee_count=attendee_count,
                my_attendance=my_attendance,
                created_at=event.created_at,
                updated_at=event.updated_at
            ))
        
        return GroupEventListResponse(
            events=events_response,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이벤트 목록 조회 중 오류가 발생했습니다."
        )

@app.put("/groups/{group_id}/events/{event_id}/", response_model=GroupEventResponse)
async def update_group_event(
    group_id: int,
    event_id: int,
    event_data: GroupEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 이벤트를 수정합니다."""
    try:
        # 이벤트 조회
        event = db.query(GroupEvent).filter(
            GroupEvent.event_id == event_id,
            GroupEvent.group_id == group_id,
            GroupEvent.is_deleted == False
        ).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이벤트를 찾을 수 없습니다."
            )
        
        # 권한 확인 (owner, admin 또는 생성자)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member or (member.role not in ['owner', 'admin'] and event.created_by != current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이벤트 수정 권한이 없습니다."
            )
        
        # 업데이트
        if event_data.title is not None:
            event.title = event_data.title
        if event_data.description is not None:
            event.description = event_data.description
        if event_data.event_date is not None:
            event.event_date = event_data.event_date
        if event_data.event_time is not None:
            event.event_time = event_data.event_time
        if event_data.location is not None:
            event.location = event_data.location
        if event_data.max_attendees is not None:
            event.max_attendees = event_data.max_attendees
        if event_data.is_mandatory is not None:
            event.is_mandatory = event_data.is_mandatory
        
        db.commit()
        db.refresh(event)
        
        # 응답 생성
        attendee_count = db.query(GroupEventAttendance).filter(
            GroupEventAttendance.event_id == event.event_id
        ).count()
        
        my_attendance_record = db.query(GroupEventAttendance).filter(
            GroupEventAttendance.event_id == event.event_id,
            GroupEventAttendance.user_id == current_user.user_id
        ).first()
        
        creator = db.query(User).filter(User.user_id == event.created_by).first()
        
        return GroupEventResponse(
            event_id=event.event_id,
            group_id=event.group_id,
            title=event.title,
            description=event.description,
            event_date=event.event_date,
            event_time=event.event_time,
            location=event.location,
            max_attendees=event.max_attendees,
            is_mandatory=event.is_mandatory,
            created_by=event.created_by,
            creator_name=creator.name if creator else "알 수 없음",
            attendee_count=attendee_count,
            my_attendance=my_attendance_record.status if my_attendance_record else None,
            created_at=event.created_at,
            updated_at=event.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이벤트 수정 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/events/{event_id}/")
async def delete_group_event(
    group_id: int,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 이벤트를 삭제합니다."""
    try:
        # 이벤트 조회
        event = db.query(GroupEvent).filter(
            GroupEvent.event_id == event_id,
            GroupEvent.group_id == group_id,
            GroupEvent.is_deleted == False
        ).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이벤트를 찾을 수 없습니다."
            )
        
        # 권한 확인 (owner, admin 또는 생성자)
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member or (member.role not in ['owner', 'admin'] and event.created_by != current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이벤트 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        event.is_deleted = True
        db.commit()
        
        return {"message": "이벤트가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이벤트 삭제 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/events/{event_id}/attend/", response_model=GroupEventAttendanceResponse)
async def attend_group_event(
    group_id: int,
    event_id: int,
    attendance_data: GroupEventAttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 이벤트 참석/불참을 등록합니다."""
    try:
        # 이벤트 조회
        event = db.query(GroupEvent).filter(
            GroupEvent.event_id == event_id,
            GroupEvent.group_id == group_id,
            GroupEvent.is_deleted == False
        ).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이벤트를 찾을 수 없습니다."
            )
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 이벤트에 참석할 수 있습니다."
            )
        
        # 기존 참석 기록 확인
        attendance = db.query(GroupEventAttendance).filter(
            GroupEventAttendance.event_id == event_id,
            GroupEventAttendance.user_id == current_user.user_id
        ).first()
        
        if attendance:
            # 업데이트
            attendance.status = attendance_data.status
        else:
            # 신규 생성
            attendance = GroupEventAttendance(
                event_id=event_id,
                user_id=current_user.user_id,
                status=attendance_data.status
            )
            db.add(attendance)
        
        db.commit()
        
        # 참석자 수 계산
        attendee_count = db.query(GroupEventAttendance).filter(
            GroupEventAttendance.event_id == event_id,
            GroupEventAttendance.status == 'attending'
        ).count()
        
        return GroupEventAttendanceResponse(
            message="참석 신청이 완료되었습니다.",
            attendee_count=attendee_count,
            my_attendance=attendance_data.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이벤트 참석 처리 중 오류가 발생했습니다."
        )

# =============================================================================
# 멤버 추방 API
# =============================================================================

@app.delete("/groups/{group_id}/members/{user_id}/")
async def remove_group_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹에서 멤버를 추방합니다."""
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(
            Group.group_id == group_id,
            Group.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        
        # 권한 확인 (owner 또는 admin만 가능)
        my_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.is_active == True
        ).first()
        
        if not my_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="멤버 추방 권한이 없습니다."
            )
        
        # 추방할 멤버 조회
        target_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.is_active == True
        ).first()
        
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="멤버를 찾을 수 없습니다."
            )
        
        # owner는 추방할 수 없음
        if target_member.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 소유자는 추방할 수 없습니다."
            )
        
        # 본인은 추방할 수 없음 (탈퇴 API 사용)
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="본인은 추방할 수 없습니다. 탈퇴 API를 사용하세요."
            )
        
        # 멤버 비활성화
        target_member.is_active = False
        target_member.left_at = db.func.current_timestamp()
        
        db.commit()
        
        # 추방된 사용자 정보
        removed_user = db.query(User).filter(User.user_id == user_id).first()
        
        return {
            "message": "멤버가 추방되었습니다.",
            "removed_user_id": user_id,
            "removed_user_name": removed_user.name if removed_user else "알 수 없음"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="멤버 추방 중 오류가 발생했습니다."
        )

# =============================================================================
# 갤러리 좋아요/댓글 API
# =============================================================================

@app.post("/groups/{group_id}/gallery/{image_id}/like/", response_model=GalleryImageLikeResponse)
async def toggle_gallery_image_like(
    group_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """갤러리 이미지 좋아요를 토글합니다."""
    try:
        # 이미지 존재 확인
        image = db.query(GroupGallery).filter(
            GroupGallery.image_id == image_id,
            GroupGallery.group_id == group_id,
            GroupGallery.is_deleted == False
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 좋아요를 할 수 있습니다."
            )
        
        # 기존 좋아요 확인
        existing_like = db.query(GalleryImageLike).filter(
            GalleryImageLike.image_id == image_id,
            GalleryImageLike.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            # 좋아요 취소
            db.delete(existing_like)
            is_liked = False
        else:
            # 좋아요 추가
            new_like = GalleryImageLike(
                image_id=image_id,
                user_id=current_user.user_id
            )
            db.add(new_like)
            is_liked = True
        
        db.commit()
        
        # 좋아요 수 계산
        like_count = db.query(GalleryImageLike).filter(
            GalleryImageLike.image_id == image_id
        ).count()
        
        return GalleryImageLikeResponse(
            image_id=image_id,
            like_count=like_count,
            is_liked=is_liked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 처리 중 오류가 발생했습니다."
        )

@app.post("/groups/{group_id}/gallery/{image_id}/comments/", response_model=GalleryImageCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_gallery_comment(
    group_id: int,
    image_id: int,
    comment_data: GalleryImageCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """갤러리 이미지에 댓글을 작성합니다."""
    try:
        # 이미지 존재 확인
        image = db.query(GroupGallery).filter(
            GroupGallery.image_id == image_id,
            GroupGallery.group_id == group_id,
            GroupGallery.is_deleted == False
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 댓글을 작성할 수 있습니다."
            )
        
        # 댓글 생성
        new_comment = GalleryImageComment(
            image_id=image_id,
            user_id=current_user.user_id,
            content=comment_data.content
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return GalleryImageCommentResponse(
            comment_id=new_comment.comment_id,
            image_id=new_comment.image_id,
            user_id=new_comment.user_id,
            user_name=current_user.name,
            content=new_comment.content,
            is_deleted=new_comment.is_deleted,
            created_at=new_comment.created_at,
            updated_at=new_comment.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 생성 중 오류가 발생했습니다."
        )

@app.get("/groups/{group_id}/gallery/{image_id}/comments/", response_model=GalleryImageCommentListResponse)
async def get_gallery_comments(
    group_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """갤러리 이미지의 댓글 목록을 조회합니다."""
    try:
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 댓글을 조회할 수 있습니다."
            )
        
        # 댓글 조회
        comments = db.query(GalleryImageComment).filter(
            GalleryImageComment.image_id == image_id,
            GalleryImageComment.is_deleted == False
        ).order_by(GalleryImageComment.created_at.asc()).all()
        
        # 응답 생성
        comments_response = []
        for comment in comments:
            user = db.query(User).filter(User.user_id == comment.user_id).first()
            comments_response.append(GalleryImageCommentResponse(
                comment_id=comment.comment_id,
                image_id=comment.image_id,
                user_id=comment.user_id,
                user_name=user.name if user else "알 수 없음",
                content=comment.content,
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            ))
        
        return GalleryImageCommentListResponse(
            comments=comments_response,
            total_count=len(comments_response)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 조회 중 오류가 발생했습니다."
        )

# =============================================================================
# 게시글 좋아요 API
# =============================================================================

@app.post("/groups/{group_id}/posts/{post_id}/like/", response_model=GroupPostLikeResponse)
async def toggle_post_like(
    group_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """게시글 좋아요를 토글합니다."""
    try:
        # 게시글 존재 확인
        post = db.query(GroupPost).filter(
            GroupPost.post_id == post_id,
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 좋아요를 할 수 있습니다."
            )
        
        # 기존 좋아요 확인
        existing_like = db.query(GroupPostLike).filter(
            GroupPostLike.post_id == post_id,
            GroupPostLike.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            # 좋아요 취소
            db.delete(existing_like)
            is_liked = False
        else:
            # 좋아요 추가
            new_like = GroupPostLike(
                post_id=post_id,
                user_id=current_user.user_id
            )
            db.add(new_like)
            is_liked = True
        
        db.commit()
        
        # 좋아요 수 계산
        like_count = db.query(GroupPostLike).filter(
            GroupPostLike.post_id == post_id
        ).count()
        
        return GroupPostLikeResponse(
            post_id=post_id,
            like_count=like_count,
            is_liked=is_liked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 처리 중 오류가 발생했습니다."
        )

# =============================================================================
# 게시글 검색 API
# =============================================================================

@app.get("/groups/{group_id}/posts/search/", response_model=GroupPostSearchResponse)
async def search_group_posts(
    group_id: int,
    q: str,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """게시글을 검색합니다 (제목 + 내용)."""
    try:
        # 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 게시글을 검색할 수 있습니다."
            )
        
        # 검색
        search_term = f"%{q}%"
        query = db.query(GroupPost).filter(
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False,
            (GroupPost.title.like(search_term) | GroupPost.content.like(search_term))
        )
        
        total_count = query.count()
        offset = (page - 1) * size
        posts = query.order_by(GroupPost.created_at.desc()).offset(offset).limit(size).all()
        
        # 응답 생성
        posts_response = []
        for post in posts:
            author = db.query(User).filter(User.user_id == post.author_id).first()
            comment_count = db.query(GroupPostComment).filter(
                GroupPostComment.post_id == post.post_id,
                GroupPostComment.is_deleted == False
            ).count()
            
            like_count = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == post.post_id
            ).count()
            
            is_liked = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == post.post_id,
                GroupPostLike.user_id == current_user.user_id
            ).first() is not None
            
            posts_response.append(GroupPostResponse(
                post_id=post.post_id,
                group_id=post.group_id,
                author_id=post.author_id,
                author_name=author.name if author else "알 수 없음",
                title=post.title,
                content=post.content,
                category=post.category or "일반",
                is_pinned=post.is_pinned,
                like_count=like_count,
                is_liked=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at,
                comment_count=comment_count
            ))
        
        return GroupPostSearchResponse(
            posts=posts_response,
            total_count=total_count,
            page=page,
            size=size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 검색 중 오류가 발생했습니다."
        )

# =============================================================================
# 게시글 이미지 업로드 API
# =============================================================================

@app.post("/groups/{group_id}/posts/{post_id}/images/", response_model=GroupPostImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_post_image(
    group_id: int,
    post_id: int,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """게시글에 이미지를 업로드합니다."""
    try:
        # 게시글 존재 확인
        post = db.query(GroupPost).filter(
            GroupPost.post_id == post_id,
            GroupPost.group_id == group_id,
            GroupPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 권한 확인 (작성자만 이미지 추가 가능)
        if post.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="게시글 작성자만 이미지를 추가할 수 있습니다."
            )
        
        # 이미지 저장
        from app.services.image_service import save_image
        image_url = await save_image(image, f"post_{post_id}")
        
        # 기존 이미지 개수 확인 (순서 결정)
        max_order = db.query(func.max(GroupPostImage.display_order)).filter(
            GroupPostImage.post_id == post_id,
            GroupPostImage.is_deleted == False
        ).scalar() or 0
        
        # 1. 게시글 이미지 테이블에 저장
        post_image = GroupPostImage(
            post_id=post_id,
            image_url=image_url,
            file_name=image.filename,
            file_size=0,  # 실제 파일 크기 계산 필요
            display_order=max_order + 1
        )
        db.add(post_image)
        
        # 2. 갤러리에도 동시에 저장
        gallery_image = GroupGallery(
            group_id=group_id,
            uploaded_by=current_user.user_id,
            image_url=image_url,
            file_name=image.filename,
            file_size=0,
            description=f"게시글 '{post.title}'의 이미지"
        )
        db.add(gallery_image)
        
        db.commit()
        db.refresh(post_image)
        
        
        return GroupPostImageResponse(
            image_id=post_image.image_id,
            post_id=post_image.post_id,
            image_url=post_image.image_url,
            created_at=post_image.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 업로드 중 오류가 발생했습니다."
        )

@app.delete("/groups/{group_id}/posts/{post_id}/images/{image_id}")
async def delete_post_image(
    group_id: int,
    post_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """게시글 이미지를 삭제합니다."""
    try:
        # 이미지 조회
        post_image = db.query(GroupPostImage).filter(
            GroupPostImage.image_id == image_id,
            GroupPostImage.post_id == post_id,
            GroupPostImage.is_deleted == False
        ).first()
        
        if not post_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 게시글 작성자 확인
        post = db.query(GroupPost).filter(GroupPost.post_id == post_id).first()
        if not post or post.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이미지 삭제 권한이 없습니다."
            )
        
        # 소프트 삭제
        post_image.is_deleted = True
        db.commit()
        
        return {"message": "이미지가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 삭제 중 오류가 발생했습니다."
        )

# =============================================================================
# 댓글 좋아요 API
# =============================================================================

@app.post("/groups/{group_id}/posts/{post_id}/comments/{comment_id}/like/", response_model=GroupPostCommentLikeResponse)
async def toggle_comment_like(
    group_id: int,
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """댓글 좋아요를 토글합니다."""
    try:
        # 댓글 존재 확인
        comment = db.query(GroupPostComment).filter(
            GroupPostComment.comment_id == comment_id,
            GroupPostComment.post_id == post_id,
            GroupPostComment.is_deleted == False
        ).first()
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="댓글을 찾을 수 없습니다."
            )
        
        # 그룹 멤버 확인
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.user_id,
            GroupMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="그룹 멤버만 댓글에 좋아요를 할 수 있습니다."
            )
        
        # 기존 좋아요 확인
        existing_like = db.query(GroupPostCommentLike).filter(
            GroupPostCommentLike.comment_id == comment_id,
            GroupPostCommentLike.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            # 좋아요 취소
            db.delete(existing_like)
            is_liked = False
        else:
            # 좋아요 추가
            new_like = GroupPostCommentLike(
                comment_id=comment_id,
                user_id=current_user.user_id
            )
            db.add(new_like)
            is_liked = True
        
        db.commit()
        
        # 좋아요 수 계산
        like_count = db.query(GroupPostCommentLike).filter(
            GroupPostCommentLike.comment_id == comment_id
        ).count()
        
        return GroupPostCommentLikeResponse(
            comment_id=comment_id,
            like_count=like_count,
            is_liked=is_liked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 좋아요 처리 중 오류가 발생했습니다."
        )

# =============================================================================
# 마이페이지 - 활동 내역 API
# =============================================================================

@app.get("/users/me/posts/", response_model=GroupPostListResponse)
async def get_my_posts(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 작성한 게시글 목록을 조회합니다."""
    try:
        # 내가 쓴 게시글 조회
        query = db.query(GroupPost).filter(
            GroupPost.author_id == current_user.user_id,
            GroupPost.is_deleted == False
        )
        
        total_count = query.count()
        offset = (page - 1) * size
        posts = query.order_by(GroupPost.created_at.desc()).offset(offset).limit(size).all()
        
        # 응답 생성
        posts_response = []
        for post in posts:
            # 그룹 정보 조회
            group = db.query(Group).filter(Group.group_id == post.group_id).first()
            
            comment_count = db.query(GroupPostComment).filter(
                GroupPostComment.post_id == post.post_id,
                GroupPostComment.is_deleted == False
            ).count()
            
            like_count = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == post.post_id
            ).count()
            
            is_liked = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == post.post_id,
                GroupPostLike.user_id == current_user.user_id
            ).first() is not None
            
            posts_response.append(GroupPostResponse(
                post_id=post.post_id,
                group_id=post.group_id,
                author_id=post.author_id,
                author_name=current_user.name,
                title=post.title,
                content=post.content,
                category=post.category or "일반",
                is_pinned=post.is_pinned,
                like_count=like_count,
                is_liked=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at,
                comment_count=comment_count
            ))
        
        return GroupPostListResponse(
            posts=posts_response,
            total_count=total_count
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 조회 중 오류가 발생했습니다."
        )

@app.get("/users/me/comments/", response_model=GroupPostCommentListResponse)
async def get_my_comments(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 작성한 댓글 목록을 조회합니다."""
    try:
        # 내가 쓴 댓글 조회
        query = db.query(GroupPostComment).filter(
            GroupPostComment.author_id == current_user.user_id,
            GroupPostComment.is_deleted == False
        )
        
        total_count = query.count()
        offset = (page - 1) * size
        comments = query.order_by(GroupPostComment.created_at.desc()).offset(offset).limit(size).all()
        
        # 응답 생성
        comments_response = []
        for comment in comments:
            # 게시글 정보 조회
            post = db.query(GroupPost).filter(GroupPost.post_id == comment.post_id).first()
            
            # 그룹 정보 조회
            group = None
            if post:
                group = db.query(Group).filter(Group.group_id == post.group_id).first()
            
            # 좋아요 수 계산
            like_count = db.query(GroupPostCommentLike).filter(
                GroupPostCommentLike.comment_id == comment.comment_id
            ).count()
            
            is_liked = db.query(GroupPostCommentLike).filter(
                GroupPostCommentLike.comment_id == comment.comment_id,
                GroupPostCommentLike.user_id == current_user.user_id
            ).first() is not None
            
            comments_response.append(GroupPostCommentResponse(
                comment_id=comment.comment_id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_name=current_user.name,
                content=comment.content,
                parent_comment_id=comment.parent_comment_id,
                is_deleted=comment.is_deleted,
                like_count=like_count,
                is_liked=is_liked,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            ))
        
        return GroupPostCommentListResponse(
            comments=comments_response,
            total_count=total_count
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 조회 중 오류가 발생했습니다."
        )


# =============================================================================
# 구해요 (구인구직) API
# =============================================================================

def calculate_is_urgent(deadline_at: datetime) -> bool:
    """마감임박 여부 계산 (24시간 이내)"""
    if not deadline_at:
        return False
    now = datetime.now()
    time_diff = deadline_at - now
    return 0 < time_diff.total_seconds() <= 24 * 60 * 60

def calculate_is_closed(deadline_at: datetime, is_closed: bool) -> bool:
    """마감 여부 계산"""
    if is_closed:
        return True
    if deadline_at and deadline_at < datetime.now():
        return True
    return False

# -----------------------------------------------------------------------------
# 게시글 CRUD
# -----------------------------------------------------------------------------

@app.get("/recruit/posts/", response_model=RecruitPostListResponse)
async def get_recruit_posts(
    page: int = 1,
    size: int = 20,
    category: Optional[str] = None,
    sort: str = "latest",  # latest, popular, deadline
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 목록 조회"""
    try:
        query = db.query(RecruitPost).filter(RecruitPost.is_deleted == False)
        
        # 카테고리 필터
        if category and category != "전체":
            query = query.filter(RecruitPost.category == category)
        
        # 검색어 필터
        if q:
            search_term = f"%{q}%"
            query = query.filter(
                (RecruitPost.title.like(search_term)) |
                (RecruitPost.content.like(search_term)) |
                (RecruitPost.tags.like(search_term))
            )
        
        # 정렬
        if sort == "popular":
            query = query.order_by(RecruitPost.like_count.desc(), RecruitPost.created_at.desc())
        elif sort == "deadline":
            query = query.filter(RecruitPost.deadline_at != None).order_by(RecruitPost.deadline_at.asc())
        else:  # latest
            query = query.order_by(RecruitPost.created_at.desc())
        
        total_count = query.count()
        offset = (page - 1) * size
        posts = query.offset(offset).limit(size).all()
        
        posts_response = []
        for post in posts:
            author = db.query(User).filter(User.user_id == post.author_id).first()
            # 대표 프로필 이미지 조회
            author_image = db.query(UserImage).filter(
                UserImage.user_id == post.author_id,
                UserImage.is_primary == True
            ).first()
            
            is_liked = db.query(RecruitPostLike).filter(
                RecruitPostLike.post_id == post.post_id,
                RecruitPostLike.user_id == current_user.user_id
            ).first() is not None
            
            # JSON 파싱
            tags_list = []
            if post.tags:
                try:
                    tags_list = json.loads(post.tags) if isinstance(post.tags, str) else post.tags
                except:
                    tags_list = []
            
            questions_list = []
            if post.questions:
                try:
                    questions_list = json.loads(post.questions) if isinstance(post.questions, str) else post.questions
                except:
                    questions_list = []
            
            posts_response.append(RecruitPostResponse(
                post_id=post.post_id,
                author_id=post.author_id,
                author_name=author.name if author else "Unknown",
                author_profile_image=author_image.image_url if author_image else None,
                title=post.title,
                content=post.content,
                image_url=post.image_url,
                category=post.category,
                tags=tags_list,
                headcount=post.headcount,
                deadline_at=post.deadline_at,
                questions=questions_list,
                view_count=post.view_count,
                like_count=post.like_count,
                comment_count=post.comment_count,
                is_liked=is_liked,
                is_urgent=calculate_is_urgent(post.deadline_at),
                is_closed=calculate_is_closed(post.deadline_at, post.is_closed),
                created_at=post.created_at,
                updated_at=post.updated_at
            ))
        
        return RecruitPostListResponse(
            posts=posts_response,
            total_count=total_count,
            page=page,
            size=size
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 목록 조회 중 오류가 발생했습니다."
        )


@app.get("/recruit/posts/{post_id}", response_model=RecruitPostResponse)
async def get_recruit_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 상세 조회"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 조회수 증가
        post.view_count += 1
        db.commit()
        
        author = db.query(User).filter(User.user_id == post.author_id).first()
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == post.author_id,
            UserImage.is_primary == True
        ).first()
        
        is_liked = db.query(RecruitPostLike).filter(
            RecruitPostLike.post_id == post.post_id,
            RecruitPostLike.user_id == current_user.user_id
        ).first() is not None
        
        # JSON 파싱
        tags_list = []
        if post.tags:
            try:
                tags_list = json.loads(post.tags) if isinstance(post.tags, str) else post.tags
            except:
                tags_list = []
        
        questions_list = []
        if post.questions:
            try:
                questions_list = json.loads(post.questions) if isinstance(post.questions, str) else post.questions
            except:
                questions_list = []
        
        return RecruitPostResponse(
            post_id=post.post_id,
            author_id=post.author_id,
            author_name=author.name if author else "Unknown",
            author_profile_image=author_image.image_url if author_image else None,
            title=post.title,
            content=post.content,
            image_url=post.image_url,
            category=post.category,
            tags=tags_list,
            headcount=post.headcount,
            deadline_at=post.deadline_at,
            questions=questions_list,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            is_liked=is_liked,
            is_urgent=calculate_is_urgent(post.deadline_at),
            is_closed=calculate_is_closed(post.deadline_at, post.is_closed),
            created_at=post.created_at,
            updated_at=post.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 조회 중 오류가 발생했습니다."
        )


@app.post("/recruit/posts/", response_model=RecruitPostResponse, status_code=status.HTTP_201_CREATED)
async def create_recruit_post(
    post_data: RecruitPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 생성"""
    try:
        # JSON 변환
        tags_json = json.dumps(post_data.tags, ensure_ascii=False) if post_data.tags else None
        questions_json = json.dumps(post_data.questions, ensure_ascii=False) if post_data.questions else None
        
        new_post = RecruitPost(
            author_id=current_user.user_id,
            title=post_data.title,
            content=post_data.content,
            image_url=post_data.image_url,
            category=post_data.category,
            tags=tags_json,
            headcount=post_data.headcount,
            deadline_at=post_data.deadline_at,
            questions=questions_json
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        return RecruitPostResponse(
            post_id=new_post.post_id,
            author_id=new_post.author_id,
            author_name=current_user.name,
            author_profile_image=author_image.image_url if author_image else None,
            title=new_post.title,
            content=new_post.content,
            image_url=new_post.image_url,
            category=new_post.category,
            tags=post_data.tags or [],
            headcount=new_post.headcount,
            deadline_at=new_post.deadline_at,
            questions=post_data.questions or [],
            view_count=0,
            like_count=0,
            comment_count=0,
            is_liked=False,
            is_urgent=calculate_is_urgent(new_post.deadline_at),
            is_closed=False,
            created_at=new_post.created_at,
            updated_at=new_post.updated_at
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 생성 중 오류가 발생했습니다."
        )


@app.put("/recruit/posts/{post_id}", response_model=RecruitPostResponse)
async def update_recruit_post(
    post_id: int,
    post_data: RecruitPostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 수정"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        if post.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="게시글 수정 권한이 없습니다."
            )
        
        # 업데이트
        if post_data.title is not None:
            post.title = post_data.title
        if post_data.content is not None:
            post.content = post_data.content
        if post_data.image_url is not None:
            post.image_url = post_data.image_url
        if post_data.category is not None:
            post.category = post_data.category
        if post_data.tags is not None:
            post.tags = json.dumps(post_data.tags, ensure_ascii=False)
        if post_data.headcount is not None:
            post.headcount = post_data.headcount
        if post_data.deadline_at is not None:
            post.deadline_at = post_data.deadline_at
        if post_data.questions is not None:
            post.questions = json.dumps(post_data.questions, ensure_ascii=False)
        if post_data.is_closed is not None:
            post.is_closed = post_data.is_closed
        
        db.commit()
        db.refresh(post)
        
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        is_liked = db.query(RecruitPostLike).filter(
            RecruitPostLike.post_id == post.post_id,
            RecruitPostLike.user_id == current_user.user_id
        ).first() is not None
        
        # JSON 파싱
        tags_list = []
        if post.tags:
            try:
                tags_list = json.loads(post.tags)
            except:
                tags_list = []
        
        questions_list = []
        if post.questions:
            try:
                questions_list = json.loads(post.questions)
            except:
                questions_list = []
        
        return RecruitPostResponse(
            post_id=post.post_id,
            author_id=post.author_id,
            author_name=current_user.name,
            author_profile_image=author_image.image_url if author_image else None,
            title=post.title,
            content=post.content,
            image_url=post.image_url,
            category=post.category,
            tags=tags_list,
            headcount=post.headcount,
            deadline_at=post.deadline_at,
            questions=questions_list,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            is_liked=is_liked,
            is_urgent=calculate_is_urgent(post.deadline_at),
            is_closed=calculate_is_closed(post.deadline_at, post.is_closed),
            created_at=post.created_at,
            updated_at=post.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 수정 중 오류가 발생했습니다."
        )


@app.delete("/recruit/posts/{post_id}")
async def delete_recruit_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 삭제"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        if post.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="게시글 삭제 권한이 없습니다."
            )
        
        post.is_deleted = True
        db.commit()
        
        return {"message": "게시글이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 삭제 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 좋아요
# -----------------------------------------------------------------------------

@app.post("/recruit/posts/{post_id}/like/", response_model=RecruitPostLikeResponse)
async def toggle_recruit_post_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 좋아요 토글"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        existing_like = db.query(RecruitPostLike).filter(
            RecruitPostLike.post_id == post_id,
            RecruitPostLike.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            db.delete(existing_like)
            post.like_count = max(0, post.like_count - 1)
            is_liked = False
        else:
            new_like = RecruitPostLike(
                post_id=post_id,
                user_id=current_user.user_id
            )
            db.add(new_like)
            post.like_count += 1
            is_liked = True
        
        db.commit()
        
        return RecruitPostLikeResponse(
            post_id=post_id,
            like_count=post.like_count,
            is_liked=is_liked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 처리 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 댓글
# -----------------------------------------------------------------------------

@app.get("/recruit/posts/{post_id}/comments/", response_model=RecruitCommentListResponse)
async def get_recruit_comments(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 댓글 목록 조회"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 최상위 댓글만 조회
        comments = db.query(RecruitPostComment).filter(
            RecruitPostComment.post_id == post_id,
            RecruitPostComment.parent_comment_id == None,
            RecruitPostComment.is_deleted == False
        ).order_by(RecruitPostComment.created_at.asc()).all()
        
        def build_comment_response(comment):
            author = db.query(User).filter(User.user_id == comment.author_id).first()
            # 대표 프로필 이미지 조회
            author_image = db.query(UserImage).filter(
                UserImage.user_id == comment.author_id,
                UserImage.is_primary == True
            ).first()
            
            # 대댓글 조회
            replies = db.query(RecruitPostComment).filter(
                RecruitPostComment.parent_comment_id == comment.comment_id,
                RecruitPostComment.is_deleted == False
            ).order_by(RecruitPostComment.created_at.asc()).all()
            
            replies_response = []
            for reply in replies:
                reply_author = db.query(User).filter(User.user_id == reply.author_id).first()
                reply_image = db.query(UserImage).filter(
                    UserImage.user_id == reply.author_id,
                    UserImage.is_primary == True
                ).first()
                replies_response.append(RecruitCommentResponse(
                    comment_id=reply.comment_id,
                    post_id=reply.post_id,
                    author_id=reply.author_id,
                    author_name=reply_author.name if reply_author else "Unknown",
                    author_profile_image=reply_image.image_url if reply_image else None,
                    content=reply.content,
                    parent_comment_id=reply.parent_comment_id,
                    is_deleted=reply.is_deleted,
                    created_at=reply.created_at,
                    updated_at=reply.updated_at,
                    replies=[]
                ))
            
            return RecruitCommentResponse(
                comment_id=comment.comment_id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_name=author.name if author else "Unknown",
                author_profile_image=author_image.image_url if author_image else None,
                content=comment.content,
                parent_comment_id=comment.parent_comment_id,
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                replies=replies_response
            )
        
        comments_response = [build_comment_response(c) for c in comments]
        total_count = db.query(RecruitPostComment).filter(
            RecruitPostComment.post_id == post_id,
            RecruitPostComment.is_deleted == False
        ).count()
        
        return RecruitCommentListResponse(
            comments=comments_response,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 목록 조회 중 오류가 발생했습니다."
        )


@app.post("/recruit/posts/{post_id}/comments/", response_model=RecruitCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_recruit_comment(
    post_id: int,
    comment_data: RecruitCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 댓글 작성"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 대댓글인 경우 부모 댓글 확인
        if comment_data.parent_comment_id:
            parent = db.query(RecruitPostComment).filter(
                RecruitPostComment.comment_id == comment_data.parent_comment_id,
                RecruitPostComment.is_deleted == False
            ).first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="부모 댓글을 찾을 수 없습니다."
                )
        
        new_comment = RecruitPostComment(
            post_id=post_id,
            author_id=current_user.user_id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id
        )
        
        db.add(new_comment)
        post.comment_count += 1
        db.commit()
        db.refresh(new_comment)
        
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        return RecruitCommentResponse(
            comment_id=new_comment.comment_id,
            post_id=new_comment.post_id,
            author_id=new_comment.author_id,
            author_name=current_user.name,
            author_profile_image=author_image.image_url if author_image else None,
            content=new_comment.content,
            parent_comment_id=new_comment.parent_comment_id,
            is_deleted=new_comment.is_deleted,
            created_at=new_comment.created_at,
            updated_at=new_comment.updated_at,
            replies=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 작성 중 오류가 발생했습니다."
        )


@app.put("/recruit/posts/{post_id}/comments/{comment_id}", response_model=RecruitCommentResponse)
async def update_recruit_comment(
    post_id: int,
    comment_id: int,
    comment_data: RecruitCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 댓글 수정"""
    try:
        comment = db.query(RecruitPostComment).filter(
            RecruitPostComment.comment_id == comment_id,
            RecruitPostComment.post_id == post_id,
            RecruitPostComment.is_deleted == False
        ).first()
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="댓글을 찾을 수 없습니다."
            )
        
        if comment.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="댓글 수정 권한이 없습니다."
            )
        
        comment.content = comment_data.content
        db.commit()
        db.refresh(comment)
        
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        return RecruitCommentResponse(
            comment_id=comment.comment_id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_name=current_user.name,
            author_profile_image=author_image.image_url if author_image else None,
            content=comment.content,
            parent_comment_id=comment.parent_comment_id,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 수정 중 오류가 발생했습니다."
        )


@app.delete("/recruit/posts/{post_id}/comments/{comment_id}")
async def delete_recruit_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글 댓글 삭제"""
    try:
        comment = db.query(RecruitPostComment).filter(
            RecruitPostComment.comment_id == comment_id,
            RecruitPostComment.post_id == post_id,
            RecruitPostComment.is_deleted == False
        ).first()
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="댓글을 찾을 수 없습니다."
            )
        
        if comment.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="댓글 삭제 권한이 없습니다."
            )
        
        comment.is_deleted = True
        
        # 게시글 댓글 수 감소
        post = db.query(RecruitPost).filter(RecruitPost.post_id == post_id).first()
        if post:
            post.comment_count = max(0, post.comment_count - 1)
        
        db.commit()
        
        return {"message": "댓글이 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 삭제 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 지원서
# -----------------------------------------------------------------------------

@app.post("/recruit/posts/{post_id}/applications/", response_model=RecruitApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_recruit_application(
    post_id: int,
    application_data: RecruitApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글에 지원서 제출"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        if post.author_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="본인 게시글에는 지원할 수 없습니다."
            )
        
        if calculate_is_closed(post.deadline_at, post.is_closed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="모집이 마감되었습니다."
            )
        
        # 중복 지원 확인
        existing = db.query(RecruitApplication).filter(
            RecruitApplication.post_id == post_id,
            RecruitApplication.applicant_id == current_user.user_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 지원한 게시글입니다."
            )
        
        # 답변을 JSON으로 변환
        answers_json = json.dumps([a.model_dump() for a in application_data.answers], ensure_ascii=False)
        
        new_application = RecruitApplication(
            post_id=post_id,
            applicant_id=current_user.user_id,
            answers=answers_json
        )
        
        db.add(new_application)
        db.commit()
        db.refresh(new_application)
        
        # 대표 프로필 이미지 조회
        applicant_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        return RecruitApplicationResponse(
            application_id=new_application.application_id,
            post_id=new_application.post_id,
            applicant_id=new_application.applicant_id,
            applicant_name=current_user.name,
            applicant_profile_image=applicant_image.image_url if applicant_image else None,
            answers=application_data.answers,
            status=new_application.status,
            is_read=new_application.is_read,
            created_at=new_application.created_at,
            updated_at=new_application.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지원서 제출 중 오류가 발생했습니다."
        )


@app.get("/recruit/posts/{post_id}/applications/", response_model=RecruitApplicationListResponse)
async def get_recruit_applications(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 게시글에 받은 지원서 목록 조회 (작성자 전용)"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        if post.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="지원서를 볼 권한이 없습니다."
            )
        
        applications = db.query(RecruitApplication).filter(
            RecruitApplication.post_id == post_id
        ).order_by(RecruitApplication.created_at.desc()).all()
        
        applications_response = []
        for app in applications:
            applicant = db.query(User).filter(User.user_id == app.applicant_id).first()
            # 대표 프로필 이미지 조회
            applicant_image = db.query(UserImage).filter(
                UserImage.user_id == app.applicant_id,
                UserImage.is_primary == True
            ).first()
            
            # JSON 파싱
            answers_list = []
            if app.answers:
                try:
                    raw_answers = json.loads(app.answers)
                    answers_list = [RecruitAnswerItem(**a) for a in raw_answers]
                except:
                    answers_list = []
            
            applications_response.append(RecruitApplicationResponse(
                application_id=app.application_id,
                post_id=app.post_id,
                applicant_id=app.applicant_id,
                applicant_name=applicant.name if applicant else "Unknown",
                applicant_profile_image=applicant_image.image_url if applicant_image else None,
                answers=answers_list,
                status=app.status,
                is_read=app.is_read,
                created_at=app.created_at,
                updated_at=app.updated_at
            ))
        
        return RecruitApplicationListResponse(
            applications=applications_response,
            total_count=len(applications_response)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지원서 목록 조회 중 오류가 발생했습니다."
        )


@app.put("/recruit/posts/{post_id}/applications/{application_id}", response_model=RecruitApplicationResponse)
async def update_recruit_application_status(
    post_id: int,
    application_id: int,
    status_data: RecruitApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구해요 지원서 상태 변경 (작성자 전용)"""
    try:
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        if post.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="지원서 상태를 변경할 권한이 없습니다."
            )
        
        application = db.query(RecruitApplication).filter(
            RecruitApplication.application_id == application_id,
            RecruitApplication.post_id == post_id
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="지원서를 찾을 수 없습니다."
            )
        
        if status_data.status not in ['pending', 'accepted', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 상태입니다."
            )
        
        application.status = status_data.status
        application.is_read = True
        db.commit()
        db.refresh(application)
        
        applicant = db.query(User).filter(User.user_id == application.applicant_id).first()
        # 대표 프로필 이미지 조회
        applicant_image = db.query(UserImage).filter(
            UserImage.user_id == application.applicant_id,
            UserImage.is_primary == True
        ).first()
        
        # JSON 파싱
        answers_list = []
        if application.answers:
            try:
                raw_answers = json.loads(application.answers)
                answers_list = [RecruitAnswerItem(**a) for a in raw_answers]
            except:
                answers_list = []
        
        return RecruitApplicationResponse(
            application_id=application.application_id,
            post_id=application.post_id,
            applicant_id=application.applicant_id,
            applicant_name=applicant.name if applicant else "Unknown",
            applicant_profile_image=applicant_image.image_url if applicant_image else None,
            answers=answers_list,
            status=application.status,
            is_read=application.is_read,
            created_at=application.created_at,
            updated_at=application.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지원서 상태 변경 중 오류가 발생했습니다."
        )


@app.delete("/recruit/posts/{post_id}/applications/me/", status_code=status.HTTP_200_OK)
async def cancel_my_recruit_application(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 지원 취소"""
    try:
        # 게시글 확인
        post = db.query(RecruitPost).filter(
            RecruitPost.post_id == post_id,
            RecruitPost.is_deleted == False
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다."
            )
        
        # 내 지원서 찾기
        application = db.query(RecruitApplication).filter(
            RecruitApplication.post_id == post_id,
            RecruitApplication.applicant_id == current_user.user_id
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="지원 내역을 찾을 수 없습니다."
            )
        
        # 이미 수락/거절된 지원은 취소 불가
        if application.status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리된 지원은 취소할 수 없습니다."
            )
        
        # 지원 삭제
        db.delete(application)
        db.commit()
        
        return {"message": "지원이 취소되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지원 취소 중 오류가 발생했습니다."
        )


@app.get("/users/me/recruit-applications/", response_model=MyRecruitApplicationListResponse)
async def get_my_recruit_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 지원한 목록 조회"""
    try:
        applications = db.query(RecruitApplication).filter(
            RecruitApplication.applicant_id == current_user.user_id
        ).order_by(RecruitApplication.created_at.desc()).all()
        
        applications_response = []
        for app in applications:
            post = db.query(RecruitPost).filter(RecruitPost.post_id == app.post_id).first()
            if not post:
                continue
            
            post_author = db.query(User).filter(User.user_id == post.author_id).first()
            
            # JSON 파싱
            answers_list = []
            if app.answers:
                try:
                    raw_answers = json.loads(app.answers)
                    answers_list = [RecruitAnswerItem(**a) for a in raw_answers]
                except:
                    answers_list = []
            
            applications_response.append(MyRecruitApplicationResponse(
                application_id=app.application_id,
                post_id=app.post_id,
                post_title=post.title,
                post_author_name=post_author.name if post_author else "Unknown",
                answers=answers_list,
                status=app.status,
                created_at=app.created_at
            ))
        
        return MyRecruitApplicationListResponse(
            applications=applications_response,
            total_count=len(applications_response)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지원 목록 조회 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 이미지 업로드
# -----------------------------------------------------------------------------

@app.post("/recruit/posts/images/", response_model=RecruitImageUploadResponse)
async def upload_recruit_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """구해요 게시글 이미지 업로드"""
    try:
        # 이미지 저장 경로
        import os
        import uuid
        
        upload_dir = "static/images/recruit"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일 확장자 확인
        ext = file.filename.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 이미지 형식입니다."
            )
        
        # 고유 파일명 생성
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        # 파일 저장
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        
        image_url = f"/static/images/recruit/{filename}"
        
        return RecruitImageUploadResponse(image_url=image_url)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 업로드 중 오류가 발생했습니다."
        )


# =============================================================================
# 장소 추천 (Place) API
# =============================================================================

# -----------------------------------------------------------------------------
# 장소 CRUD
# -----------------------------------------------------------------------------

@app.get("/places/", response_model=PlaceListResponse)
async def get_places(
    page: int = 1,
    size: int = 20,
    category: Optional[str] = None,
    sort: str = "popular",  # popular, latest, likes, rating
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 목록 조회"""
    try:
        query = db.query(Place).filter(Place.is_deleted == False)
        
        # 카테고리 필터
        if category:
            query = query.filter(Place.category == category)
        
        # 검색어 필터
        if q:
            search_term = f"%{q}%"
            query = query.filter(
                (Place.title.like(search_term)) |
                (Place.address.like(search_term))
            )
        
        # 정렬
        if sort == "latest":
            query = query.order_by(Place.created_at.desc())
        elif sort == "likes":
            query = query.order_by(Place.like_count.desc(), Place.created_at.desc())
        elif sort == "rating":
            query = query.order_by(Place.avg_rating.desc(), Place.created_at.desc())
        else:  # popular
            query = query.order_by(Place.view_count.desc(), Place.created_at.desc())
        
        total_count = query.count()
        offset = (page - 1) * size
        places = query.offset(offset).limit(size).all()
        
        places_response = []
        for place in places:
            author = db.query(User).filter(User.user_id == place.author_id).first()
            
            # 대표 이미지 (첫 번째 이미지)
            first_image = db.query(PlaceImage).filter(
                PlaceImage.place_id == place.place_id
            ).order_by(PlaceImage.upload_order.asc()).first()
            
            is_liked = db.query(PlaceLike).filter(
                PlaceLike.place_id == place.place_id,
                PlaceLike.user_id == current_user.user_id
            ).first() is not None
            
            places_response.append(PlaceListItemResponse(
                place_id=place.place_id,
                author_id=place.author_id,
                author_name=author.name if author else "Unknown",
                title=place.title,
                address=place.address,
                category=place.category,
                image_url=first_image.image_url if first_image else None,
                view_count=place.view_count,
                like_count=place.like_count,
                review_count=place.review_count,
                avg_rating=place.avg_rating or 0.0,
                is_liked=is_liked,
                created_at=place.created_at
            ))
        
        return PlaceListResponse(
            places=places_response,
            total_count=total_count,
            page=page,
            size=size
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 목록 조회 중 오류가 발생했습니다."
        )


@app.get("/places/{place_id}", response_model=PlaceDetailResponse)
async def get_place_detail(
    place_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 상세 조회"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        # 조회수 증가
        place.view_count += 1
        db.commit()
        
        author = db.query(User).filter(User.user_id == place.author_id).first()
        
        # 이미지 목록
        images = db.query(PlaceImage).filter(
            PlaceImage.place_id == place_id
        ).order_by(PlaceImage.upload_order.asc()).all()
        
        images_response = [
            PlaceImageResponse(
                image_id=img.image_id,
                image_url=img.image_url,
                upload_order=img.upload_order
            ) for img in images
        ]
        
        is_liked = db.query(PlaceLike).filter(
            PlaceLike.place_id == place_id,
            PlaceLike.user_id == current_user.user_id
        ).first() is not None
        
        return PlaceDetailResponse(
            place_id=place.place_id,
            author_id=place.author_id,
            author_name=author.name if author else "Unknown",
            title=place.title,
            content=place.content,
            address=place.address,
            category=place.category,
            images=images_response,
            view_count=place.view_count,
            like_count=place.like_count,
            review_count=place.review_count,
            avg_rating=place.avg_rating or 0.0,
            is_liked=is_liked,
            created_at=place.created_at,
            updated_at=place.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 조회 중 오류가 발생했습니다."
        )


@app.post("/places/", response_model=PlaceDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_place(
    place_data: PlaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 등록"""
    try:
        new_place = Place(
            author_id=current_user.user_id,
            title=place_data.title,
            content=place_data.content,
            address=place_data.address,
            category=place_data.category
        )
        
        db.add(new_place)
        db.commit()
        db.refresh(new_place)
        
        return PlaceDetailResponse(
            place_id=new_place.place_id,
            author_id=new_place.author_id,
            author_name=current_user.name,
            title=new_place.title,
            content=new_place.content,
            address=new_place.address,
            category=new_place.category,
            images=[],
            view_count=0,
            like_count=0,
            review_count=0,
            avg_rating=0.0,
            is_liked=False,
            created_at=new_place.created_at,
            updated_at=new_place.updated_at
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 등록 중 오류가 발생했습니다."
        )


@app.put("/places/{place_id}", response_model=PlaceDetailResponse)
async def update_place(
    place_id: int,
    place_data: PlaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 수정"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        if place.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="장소 수정 권한이 없습니다."
            )
        
        # 업데이트
        if place_data.title is not None:
            place.title = place_data.title
        if place_data.content is not None:
            place.content = place_data.content
        if place_data.address is not None:
            place.address = place_data.address
        if place_data.category is not None:
            place.category = place_data.category
        
        db.commit()
        db.refresh(place)
        
        # 이미지 목록
        images = db.query(PlaceImage).filter(
            PlaceImage.place_id == place_id
        ).order_by(PlaceImage.upload_order.asc()).all()
        
        images_response = [
            PlaceImageResponse(
                image_id=img.image_id,
                image_url=img.image_url,
                upload_order=img.upload_order
            ) for img in images
        ]
        
        is_liked = db.query(PlaceLike).filter(
            PlaceLike.place_id == place_id,
            PlaceLike.user_id == current_user.user_id
        ).first() is not None
        
        return PlaceDetailResponse(
            place_id=place.place_id,
            author_id=place.author_id,
            author_name=current_user.name,
            title=place.title,
            content=place.content,
            address=place.address,
            category=place.category,
            images=images_response,
            view_count=place.view_count,
            like_count=place.like_count,
            review_count=place.review_count,
            avg_rating=place.avg_rating or 0.0,
            is_liked=is_liked,
            created_at=place.created_at,
            updated_at=place.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 수정 중 오류가 발생했습니다."
        )


@app.delete("/places/{place_id}")
async def delete_place(
    place_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 삭제"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        if place.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="장소 삭제 권한이 없습니다."
            )
        
        place.is_deleted = True
        db.commit()
        
        return {"message": "장소가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 삭제 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 장소 이미지
# -----------------------------------------------------------------------------

@app.post("/places/{place_id}/images", response_model=PlaceImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_place_image(
    place_id: int,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 이미지 업로드"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        if place.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이미지 업로드 권한이 없습니다."
            )
        
        # 이미지 저장 경로
        import os
        import uuid
        
        upload_dir = f"static/images/places"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일 확장자 확인
        ext = image.filename.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 이미지 형식입니다."
            )
        
        # 고유 파일명 생성
        filename = f"{place_id}_{uuid.uuid4()}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        # 파일 저장
        with open(filepath, "wb") as f:
            content = await image.read()
            f.write(content)
        
        image_url = f"/static/images/places/{filename}"
        
        # 현재 이미지 개수 확인
        current_count = db.query(PlaceImage).filter(
            PlaceImage.place_id == place_id
        ).count()
        
        # DB에 저장
        new_image = PlaceImage(
            place_id=place_id,
            image_url=image_url,
            upload_order=current_count
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        return PlaceImageUploadResponse(
            image_id=new_image.image_id,
            image_url=new_image.image_url,
            upload_order=new_image.upload_order
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 업로드 중 오류가 발생했습니다."
        )


@app.delete("/places/{place_id}/images/{image_id}")
async def delete_place_image(
    place_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 이미지 삭제"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        if place.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이미지 삭제 권한이 없습니다."
            )
        
        image = db.query(PlaceImage).filter(
            PlaceImage.image_id == image_id,
            PlaceImage.place_id == place_id
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지를 찾을 수 없습니다."
            )
        
        # 실제 파일 삭제
        import os
        if image.image_url.startswith('/'):
            file_path = image.image_url[1:]  # 앞의 '/' 제거
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.delete(image)
        db.commit()
        
        return {"message": "이미지가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 삭제 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 장소 좋아요
# -----------------------------------------------------------------------------

@app.post("/places/{place_id}/like", response_model=PlaceLikeResponse)
async def toggle_place_like(
    place_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """장소 좋아요 토글"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        existing_like = db.query(PlaceLike).filter(
            PlaceLike.place_id == place_id,
            PlaceLike.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            db.delete(existing_like)
            place.like_count = max(0, place.like_count - 1)
            is_liked = False
        else:
            new_like = PlaceLike(
                place_id=place_id,
                user_id=current_user.user_id
            )
            db.add(new_like)
            place.like_count += 1
            is_liked = True
        
        db.commit()
        
        return PlaceLikeResponse(
            place_id=place_id,
            is_liked=is_liked,
            like_count=place.like_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 처리 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 리뷰 CRUD
# -----------------------------------------------------------------------------

@app.get("/places/{place_id}/reviews", response_model=PlaceReviewListResponse)
async def get_place_reviews(
    place_id: int,
    page: int = 1,
    size: int = 20,
    sort: str = "latest",  # latest, rating_high, rating_low
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """리뷰 목록 조회"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        query = db.query(PlaceReview).filter(
            PlaceReview.place_id == place_id,
            PlaceReview.is_deleted == False
        )
        
        # 정렬
        if sort == "rating_high":
            query = query.order_by(PlaceReview.rating.desc(), PlaceReview.created_at.desc())
        elif sort == "rating_low":
            query = query.order_by(PlaceReview.rating.asc(), PlaceReview.created_at.desc())
        else:  # latest
            query = query.order_by(PlaceReview.created_at.desc())
        
        total_count = query.count()
        offset = (page - 1) * size
        reviews = query.offset(offset).limit(size).all()
        
        # 별점 분포 계산
        rating_dist = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        all_reviews = db.query(PlaceReview).filter(
            PlaceReview.place_id == place_id,
            PlaceReview.is_deleted == False
        ).all()
        
        for r in all_reviews:
            rating_dist[str(r.rating)] += 1
        
        reviews_response = []
        for review in reviews:
            author = db.query(User).filter(User.user_id == review.author_id).first()
            # 대표 프로필 이미지 조회
            author_image = db.query(UserImage).filter(
                UserImage.user_id == review.author_id,
                UserImage.is_primary == True
            ).first()
            
            reviews_response.append(PlaceReviewResponse(
                review_id=review.review_id,
                place_id=review.place_id,
                author_id=review.author_id,
                author_name=author.name if author else "Unknown",
                author_profile_image=author_image.image_url if author_image else None,
                rating=review.rating,
                content=review.content,
                visit_date=review.visit_date,
                created_at=review.created_at,
                updated_at=review.updated_at
            ))
        
        return PlaceReviewListResponse(
            reviews=reviews_response,
            total_count=total_count,
            avg_rating=place.avg_rating or 0.0,
            rating_distribution=rating_dist,
            page=page,
            size=size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 목록 조회 중 오류가 발생했습니다."
        )


@app.post("/places/{place_id}/reviews", response_model=PlaceReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_place_review(
    place_id: int,
    review_data: PlaceReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """리뷰 작성"""
    try:
        place = db.query(Place).filter(
            Place.place_id == place_id,
            Place.is_deleted == False
        ).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="장소를 찾을 수 없습니다."
            )
        
        # 본인 장소에는 리뷰 불가
        if place.author_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="본인이 등록한 장소에는 리뷰를 작성할 수 없습니다."
            )
        
        new_review = PlaceReview(
            place_id=place_id,
            author_id=current_user.user_id,
            rating=review_data.rating,
            content=review_data.content,
            visit_date=review_data.visit_date
        )
        
        db.add(new_review)
        
        # 리뷰 수 증가 및 평균 별점 재계산
        place.review_count += 1
        
        # 평균 별점 계산
        all_ratings = db.query(PlaceReview.rating).filter(
            PlaceReview.place_id == place_id,
            PlaceReview.is_deleted == False
        ).all()
        ratings_list = [r[0] for r in all_ratings] + [review_data.rating]
        place.avg_rating = sum(ratings_list) / len(ratings_list)
        
        db.commit()
        db.refresh(new_review)
        
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        return PlaceReviewResponse(
            review_id=new_review.review_id,
            place_id=new_review.place_id,
            author_id=new_review.author_id,
            author_name=current_user.name,
            author_profile_image=author_image.image_url if author_image else None,
            rating=new_review.rating,
            content=new_review.content,
            visit_date=new_review.visit_date,
            created_at=new_review.created_at,
            updated_at=new_review.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 작성 중 오류가 발생했습니다."
        )


@app.put("/places/{place_id}/reviews/{review_id}", response_model=PlaceReviewResponse)
async def update_place_review(
    place_id: int,
    review_id: int,
    review_data: PlaceReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """리뷰 수정"""
    try:
        review = db.query(PlaceReview).filter(
            PlaceReview.review_id == review_id,
            PlaceReview.place_id == place_id,
            PlaceReview.is_deleted == False
        ).first()
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="리뷰를 찾을 수 없습니다."
            )
        
        if review.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="리뷰 수정 권한이 없습니다."
            )
        
        old_rating = review.rating
        
        # 업데이트
        if review_data.rating is not None:
            review.rating = review_data.rating
        if review_data.content is not None:
            review.content = review_data.content
        if review_data.visit_date is not None:
            review.visit_date = review_data.visit_date
        
        # 별점이 변경된 경우 평균 재계산
        if review_data.rating is not None and review_data.rating != old_rating:
            place = db.query(Place).filter(Place.place_id == place_id).first()
            if place:
                all_ratings = db.query(PlaceReview.rating).filter(
                    PlaceReview.place_id == place_id,
                    PlaceReview.is_deleted == False,
                    PlaceReview.review_id != review_id
                ).all()
                ratings_list = [r[0] for r in all_ratings] + [review.rating]
                place.avg_rating = sum(ratings_list) / len(ratings_list)
        
        db.commit()
        db.refresh(review)
        
        # 대표 프로필 이미지 조회
        author_image = db.query(UserImage).filter(
            UserImage.user_id == current_user.user_id,
            UserImage.is_primary == True
        ).first()
        
        return PlaceReviewResponse(
            review_id=review.review_id,
            place_id=review.place_id,
            author_id=review.author_id,
            author_name=current_user.name,
            author_profile_image=author_image.image_url if author_image else None,
            rating=review.rating,
            content=review.content,
            visit_date=review.visit_date,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 수정 중 오류가 발생했습니다."
        )


@app.delete("/places/{place_id}/reviews/{review_id}")
async def delete_place_review(
    place_id: int,
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """리뷰 삭제"""
    try:
        review = db.query(PlaceReview).filter(
            PlaceReview.review_id == review_id,
            PlaceReview.place_id == place_id,
            PlaceReview.is_deleted == False
        ).first()
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="리뷰를 찾을 수 없습니다."
            )
        
        if review.author_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="리뷰 삭제 권한이 없습니다."
            )
        
        review.is_deleted = True
        
        # 리뷰 수 감소 및 평균 별점 재계산
        place = db.query(Place).filter(Place.place_id == place_id).first()
        if place:
            place.review_count = max(0, place.review_count - 1)
            
            # 평균 별점 재계산
            remaining_ratings = db.query(PlaceReview.rating).filter(
                PlaceReview.place_id == place_id,
                PlaceReview.is_deleted == False,
                PlaceReview.review_id != review_id
            ).all()
            
            if remaining_ratings:
                ratings_list = [r[0] for r in remaining_ratings]
                place.avg_rating = sum(ratings_list) / len(ratings_list)
            else:
                place.avg_rating = 0.0
        
        db.commit()
        
        return {"message": "리뷰가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 삭제 중 오류가 발생했습니다."
        )


# -----------------------------------------------------------------------------
# 내 장소/리뷰 목록
# -----------------------------------------------------------------------------

@app.get("/users/me/places", response_model=PlaceListResponse)
async def get_my_places(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 등록한 장소 목록"""
    try:
        query = db.query(Place).filter(
            Place.author_id == current_user.user_id,
            Place.is_deleted == False
        )
        
        total_count = query.count()
        offset = (page - 1) * size
        places = query.order_by(Place.created_at.desc()).offset(offset).limit(size).all()
        
        places_response = []
        for place in places:
            # 대표 이미지
            first_image = db.query(PlaceImage).filter(
                PlaceImage.place_id == place.place_id
            ).order_by(PlaceImage.upload_order.asc()).first()
            
            places_response.append(PlaceListItemResponse(
                place_id=place.place_id,
                author_id=place.author_id,
                author_name=current_user.name,
                title=place.title,
                address=place.address,
                category=place.category,
                image_url=first_image.image_url if first_image else None,
                view_count=place.view_count,
                like_count=place.like_count,
                review_count=place.review_count,
                avg_rating=place.avg_rating or 0.0,
                is_liked=False,  # 자기 장소이므로
                created_at=place.created_at
            ))
        
        return PlaceListResponse(
            places=places_response,
            total_count=total_count,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 목록 조회 중 오류가 발생했습니다."
        )


@app.get("/users/me/liked-places", response_model=PlaceListResponse)
async def get_my_liked_places(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 좋아요한 장소 목록"""
    try:
        # 좋아요한 장소 ID 목록
        liked_place_ids = db.query(PlaceLike.place_id).filter(
            PlaceLike.user_id == current_user.user_id
        ).all()
        liked_ids = [p[0] for p in liked_place_ids]
        
        query = db.query(Place).filter(
            Place.place_id.in_(liked_ids),
            Place.is_deleted == False
        )
        
        total_count = query.count()
        offset = (page - 1) * size
        places = query.order_by(Place.created_at.desc()).offset(offset).limit(size).all()
        
        places_response = []
        for place in places:
            author = db.query(User).filter(User.user_id == place.author_id).first()
            
            # 대표 이미지
            first_image = db.query(PlaceImage).filter(
                PlaceImage.place_id == place.place_id
            ).order_by(PlaceImage.upload_order.asc()).first()
            
            places_response.append(PlaceListItemResponse(
                place_id=place.place_id,
                author_id=place.author_id,
                author_name=author.name if author else "Unknown",
                title=place.title,
                address=place.address,
                category=place.category,
                image_url=first_image.image_url if first_image else None,
                view_count=place.view_count,
                like_count=place.like_count,
                review_count=place.review_count,
                avg_rating=place.avg_rating or 0.0,
                is_liked=True,
                created_at=place.created_at
            ))
        
        return PlaceListResponse(
            places=places_response,
            total_count=total_count,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="장소 목록 조회 중 오류가 발생했습니다."
        )


@app.get("/users/me/place-reviews", response_model=MyPlaceReviewListResponse)
async def get_my_place_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 작성한 리뷰 목록"""
    try:
        reviews = db.query(PlaceReview).filter(
            PlaceReview.author_id == current_user.user_id,
            PlaceReview.is_deleted == False
        ).order_by(PlaceReview.created_at.desc()).all()
        
        reviews_response = []
        for review in reviews:
            place = db.query(Place).filter(Place.place_id == review.place_id).first()
            
            reviews_response.append(MyPlaceReviewResponse(
                review_id=review.review_id,
                place_id=review.place_id,
                place_title=place.title if place else "삭제된 장소",
                rating=review.rating,
                content=review.content,
                visit_date=review.visit_date,
                created_at=review.created_at
            ))
        
        return MyPlaceReviewListResponse(
            reviews=reviews_response,
            total_count=len(reviews_response)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 목록 조회 중 오류가 발생했습니다."
        )