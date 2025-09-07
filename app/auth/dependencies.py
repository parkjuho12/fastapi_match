"""
인증 의존성 및 사용자 인증 관련 기능
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.models.database import get_db
from app.models.models import User
from app.models.schemas import TokenData
from app.auth.jwt_handler import verify_token
from app.auth.security import verify_password


def get_current_user(token_data: TokenData = Depends(verify_token), db: Session = Depends(get_db)) -> User:
    """현재 인증된 사용자 정보 반환"""
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """사용자 인증"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash, user.salt):
        return None
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()