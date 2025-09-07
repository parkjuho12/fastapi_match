"""
비밀번호 해싱 및 보안 관련 기능
"""
import hashlib
import secrets


def generate_salt() -> str:
    """16바이트 소금을 생성하고 32자 HEX 문자열로 반환"""
    return secrets.token_hex(16)


def hash_password_with_salt(password: str, salt: str) -> str:
    """비밀번호와 salt을 사용하여 SHA-256 해시 생성"""
    salted_password = password + salt
    return hashlib.sha256(salted_password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """비밀번호 검증"""
    return hash_password_with_salt(plain_password, salt) == hashed_password