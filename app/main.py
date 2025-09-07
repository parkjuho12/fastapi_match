"""
매칭 앱 FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json
from datetime import datetime
from typing import Dict, List, Optional

# 로컬 모듈 import
from app.models.database import get_db, create_tables
from app.models.models import (
    User, EmailVerification, Subject, Timetable, TimetableSubject,
    ChatRoom, ChatParticipant, ChatMessage, MessageReaction,
    UserProfile, UserImage, Notification
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
    OnboardingProgressResponse, ImageUploadResponse,
    OnboardingCompleteRequest, OnboardingCompleteResponse,
    KeywordTypeEnum,
    # 알람 관련 스키마
    NotificationCreate, NotificationResponse, NotificationListResponse,
    NotificationMarkReadRequest, NotificationStatsResponse, NotificationTypeEnum
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
        print("✅ 데이터베이스 테이블 생성/확인 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 에러: {e}")
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
        print(f"이메일 인증번호 발송 에러: {e}")
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
        print(f"이메일 인증 확인 에러: {e}")
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
        
        print(f"✅ 회원가입 성공: {user.email}")
        return db_user
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        print(f"회원가입 DB 에러: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 정보입니다."
        )
    except Exception as e:
        db.rollback()
        print(f"회원가입 에러: {e}")
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
        print(f"사용자 정보 조회 에러: {e}")
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
        print(f"로그아웃 에러: {e}")
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
        print(f"아이디 찾기 에러: {e}")
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
        print(f"비밀번호 재설정 요청 에러: {e}")
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
        print(f"인증번호 확인 에러: {e}")
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
        print(f"비밀번호 재설정 에러: {e}")
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
        
        print(f"🔍 과목 생성 요청 데이터: {request_data}")
        print(f"🔍 사용자 ID: {current_user.user_id}")
        
        # 수동으로 데이터 검증 및 처리
        subject_data = {
            'subject_name': request_data.get('subject_name', ''),
            'professor_name': request_data.get('professor_name', ''),
            'classroom': request_data.get('classroom', ''),
            'day_of_week': request_data.get('day_of_week', ''),
            'start_time': request_data.get('start_time', ''),
            'end_time': request_data.get('end_time', '')
        }
        
        print(f"🔍 처리된 과목 데이터: {subject_data}")
        
        # 시간 형태 변환
        from datetime import time
        
        start_time_str = subject_data['start_time']
        end_time_str = subject_data['end_time']
        
        # "09:00:00" 형태를 time 객체로 변환
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
        
        print(f"🔍 변환된 시간: {start_time} - {end_time}")
        # 시간 겹침 검사
        existing_subject = db.query(Subject).filter(
            Subject.user_id == current_user.user_id,
            Subject.day_of_week == subject_data['day_of_week'],
            Subject.start_time < end_time,
            Subject.end_time > start_time
        ).first()
        
        if existing_subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"해당 시간대에 이미 등록된 과목이 있습니다: {existing_subject.subject_name}"
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
        print(f"과목 생성 에러: {e}")
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
        print(f"과목 조회 에러: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="과목 조회 중 오류가 발생했습니다."
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
        print(f"과목 상세 조회 에러: {e}")
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
        print(f"과목 수정 에러: {e}")
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
        print(f"과목 삭제 에러: {e}")
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
        print(f"시간표 생성 에러: {e}")
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
        print(f"시간표 조회 에러: {e}")
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
            print(f"✅ 사용자 {current_user.user_id}에게 기본 시간표 생성됨: ID={timetable.timetable_id}")
        
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
        print(f"활성 시간표 조회 에러: {e}")
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
        print(f"시간표 과목 추가 에러: {e}")
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
        print(f"시간표 과목 제거 에러: {e}")
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
        print(f"🔗 사용자 {user_id}가 채팅방 {room_id}에 연결되었습니다.")
    
    def disconnect(self, room_id: int, user_id: int):
        if room_id in self.active_connections:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]
                print(f"❌ 사용자 {user_id}가 채팅방 {room_id}에서 연결 해제되었습니다.")
                
                # 방에 아무도 없으면 방 정보 삭제
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
    
    async def send_personal_message(self, message: str, room_id: int, user_id: int):
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            await self.active_connections[room_id][user_id].send_text(message)
    
    async def broadcast_to_room(self, message: str, room_id: int, exclude_user: int = None):
        print(f"🔊 브로드캐스트 시작 - 방 {room_id}, 제외할 사용자: {exclude_user}")
        print(f"📋 현재 활성 연결: {self.active_connections}")
        
        if room_id in self.active_connections:
            print(f"📍 방 {room_id}의 연결된 사용자들: {list(self.active_connections[room_id].keys())}")
            for user_id, websocket in self.active_connections[room_id].items():
                if exclude_user is None or user_id != exclude_user:
                    try:
                        print(f"📤 사용자 {user_id}에게 메시지 전송 중...")
                        await websocket.send_text(message)
                        print(f"✅ 사용자 {user_id}에게 메시지 전송 완료")
                    except Exception as e:
                        print(f"❌ 메시지 전송 실패 (사용자 {user_id}): {e}")
                else:
                    print(f"⏭️ 사용자 {user_id} 제외됨")
        else:
            print(f"❌ 방 {room_id}이 활성 연결에 없음")

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
        print(f"📢 입장 알림 전송 시도: {join_message}")
        try:
            await manager.broadcast_to_room(json.dumps(join_message), room_id, user.user_id)
            print(f"✅ 입장 알림 전송 완료")
        except Exception as broadcast_error:
            print(f"❌ 입장 알림 전송 실패: {broadcast_error}")
        
        print(f"🔄 메시지 수신 루프 시작 - 사용자 {user.user_id}")
        while True:
            try:
                # 메시지 수신 (타임아웃 없이 대기)
                print(f"⏳ 메시지 대기 중... - 사용자 {user.user_id}")
                data = await websocket.receive_text()
                print(f"📨 받은 메시지: {data}")
                
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 파싱 에러: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "잘못된 메시지 형식입니다."
                    }))
                    continue
                
                if message_data.get("type") == "heartbeat":
                    # 하트비트 응답
                    print(f"💓 하트비트 수신 - 사용자 {user.user_id}")
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_response",
                        "timestamp": datetime.now().isoformat()
                    }))
                    continue
                
                elif message_data.get("type") == "message":
                    print(f"💬 메시지 처리 중: {message_data}")
                    
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
                        print(f"✅ 메시지 저장 완료: {new_message.message_id}")
                    except Exception as db_error:
                        print(f"❌ 데이터베이스 저장 에러: {db_error}")
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
                        print(f"📢 메시지 브로드캐스트 완료")
                    except Exception as broadcast_error:
                        print(f"❌ 브로드캐스트 에러: {broadcast_error}")
                
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
                        print(f"⌨️ 타이핑 상태 브로드캐스트 완료")
                    except Exception as typing_error:
                        print(f"❌ 타이핑 브로드캐스트 에러: {typing_error}")
                        
            except WebSocketDisconnect:
                print("🔌 WebSocket 연결이 정상적으로 끊어졌습니다.")
                break
            except Exception as message_error:
                print(f"❌ 메시지 처리 에러: {message_error}")
                import traceback
                traceback.print_exc()
                # RuntimeError가 발생하면 연결이 끊어진 것이므로 루프 종료
                if "Cannot call \"receive\" once a disconnect message has been received" in str(message_error):
                    print("🔌 WebSocket 연결이 끊어져서 루프를 종료합니다.")
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
        print(f"WebSocket 에러: {e}")
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
        print(f"채팅방 생성 에러: {e}")
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
                unread_count=unread_count
            )
            rooms_response.append(room_response)
        
        return ChatRoomListResponse(
            rooms=rooms_response,
            total_count=len(rooms_response)
        )
        
    except Exception as e:
        print(f"채팅방 목록 조회 에러: {e}")
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
        print(f"채팅 메시지 조회 에러: {e}")
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
        print(f"온보딩 진행상황 조회 에러: {e}")
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
        print(f"온보딩 데이터 저장 에러: {e}")
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
        print(f"이미지 업로드 에러: {e}")
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
        print(f"이미지 삭제 에러: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 삭제 중 오류가 발생했습니다."
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
        print(f"온보딩 완료 처리 에러: {e}")
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
        
        # 키워드와 이미지 정보 포함
        keywords = db.query(UserKeyword).filter(UserKeyword.user_id == user_id).all()
        images = db.query(UserImage).filter(UserImage.user_id == user_id).all()
        
        response_data = profile.__dict__.copy()
        response_data['keywords'] = keywords
        response_data['images'] = images
        
        return UserProfileResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"프로필 조회 에러: {e}")
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
        print(f"개인정보 수정 에러: {e}")
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
        print(f"온보딩 프로필 조회 에러: {e}")
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
        print(f"온보딩 프로필 조회 에러: {e}")
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
        
        print(f"🔍 원시 요청 데이터: {request_data}")
        print(f"🔍 사용자 ID: {current_user.user_id}")
        
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
        
        print(f"🔍 처리된 프로필 데이터: {profile_data}")
        
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
        print(f"프로필 수정 에러: {e}")
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
        print(f"온보딩 프로필 저장 에러: {e}")
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
        print(f"알람 목록 조회 에러: {e}")
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
        print(f"알람 통계 조회 에러: {e}")
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
        print(f"알람 읽음 처리 에러: {e}")
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
        print(f"전체 알람 읽음 처리 에러: {e}")
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
        print(f"알람 삭제 에러: {e}")
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
        
        print(f"✅ 알람 생성: 사용자 {user_id}에게 '{title}' 알람 발송")
        return notification
        
    except Exception as e:
        db.rollback()
        print(f"❌ 알람 생성 에러: {e}")
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
        print(f"파일 업로드 에러: {e}")
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
        print(f"메시지 반응 추가 에러: {e}")
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
        print(f"메시지 반응 제거 에러: {e}")
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
        print(f"메시지 반응 조회 에러: {e}")
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
        print(f"메시지 검색 에러: {e}")
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
        print(f"채팅방 설정 조회 에러: {e}")
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
        print(f"채팅방 설정 업데이트 에러: {e}")
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
        print(f"예약 메시지 생성 에러: {e}")
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
        print(f"온라인 상태 조회 에러: {e}")
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
        print(f"이미지 업로드 에러: {e}")
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
        print(f"이미지 목록 조회 에러: {e}")
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
        print(f"이미지 삭제 에러: {e}")
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
        print(f"대표 이미지 설정 에러: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대표 이미지 설정 중 오류가 발생했습니다."
        )