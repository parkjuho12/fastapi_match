"""
채팅용 파일 업로드 및 처리 서비스
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import aiofiles

class FileService:
    # 허용되는 파일 형식
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx'}
    ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    
    # 최대 파일 크기 설정
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    
    # 파일 저장 디렉토리
    UPLOAD_DIR = Path("static/uploads")
    CHAT_FILES_DIR = UPLOAD_DIR / "chat"
    
    @classmethod
    def setup_directories(cls):
        """파일 저장 디렉토리 생성"""
        cls.CHAT_FILES_DIR.mkdir(parents=True, exist_ok=True)
        
        # 타입별 디렉토리 생성
        (cls.CHAT_FILES_DIR / "images").mkdir(exist_ok=True)
        (cls.CHAT_FILES_DIR / "documents").mkdir(exist_ok=True)
        (cls.CHAT_FILES_DIR / "audio").mkdir(exist_ok=True)
        (cls.CHAT_FILES_DIR / "videos").mkdir(exist_ok=True)
    
    @classmethod
    def get_file_type_and_category(cls, file: UploadFile) -> tuple[str, str]:
        """파일 타입과 카테고리 판단"""
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension in cls.ALLOWED_IMAGE_EXTENSIONS:
            return "image", "images"
        elif file_extension in cls.ALLOWED_DOCUMENT_EXTENSIONS:
            return "file", "documents"
        elif file_extension in cls.ALLOWED_AUDIO_EXTENSIONS:
            return "voice", "audio"
        elif file_extension in cls.ALLOWED_VIDEO_EXTENSIONS:
            return "file", "videos"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 파일 형식입니다. 확장자: {file_extension}"
            )
    
    @classmethod
    def get_max_file_size(cls, category: str) -> int:
        """카테고리별 최대 파일 크기 반환"""
        size_map = {
            "images": cls.MAX_IMAGE_SIZE,
            "documents": cls.MAX_DOCUMENT_SIZE,
            "audio": cls.MAX_AUDIO_SIZE,
            "videos": cls.MAX_VIDEO_SIZE
        }
        return size_map.get(category, cls.MAX_DOCUMENT_SIZE)
    
    @classmethod
    def validate_file(cls, file: UploadFile) -> tuple[str, str]:
        """파일 검증"""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일명이 없습니다."
            )
        
        # 파일 타입과 카테고리 확인
        file_type, category = cls.get_file_type_and_category(file)
        
        # 파일 크기 검증
        max_size = cls.get_max_file_size(category)
        if hasattr(file, 'size') and file.size and file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 크기가 너무 큽니다. 최대 크기: {max_size // (1024*1024)}MB"
            )
        
        return file_type, category
    
    @classmethod
    def generate_unique_filename(cls, original_filename: str) -> str:
        """고유한 파일명 생성"""
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"
    
    @classmethod
    async def save_chat_file(cls, file: UploadFile, room_id: int, user_id: int) -> Dict[str, Any]:
        """
        채팅용 파일 저장
        Returns: {file_type, file_url, file_name, file_size}
        """
        # 디렉토리 생성
        cls.setup_directories()
        
        # 파일 검증
        file_type, category = cls.validate_file(file)
        
        # 고유 파일명 생성
        unique_filename = cls.generate_unique_filename(file.filename)
        
        # 저장 경로 설정 (room_id/user_id/filename)
        save_dir = cls.CHAT_FILES_DIR / category / str(room_id) / str(user_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / unique_filename
        
        # 파일 저장
        file_size = 0
        try:
            # 파일 내용 읽기
            content = await file.read()
            file_size = len(content)
            
            # 파일 크기 재검증
            max_size = cls.get_max_file_size(category)
            if file_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"파일 크기가 너무 큽니다. 최대 크기: {max_size // (1024*1024)}MB"
                )
            
            # 파일 저장
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # 이미지인 경우 추가 검증
            if file_type == "image":
                try:
                    with Image.open(file_path) as img:
                        img.verify()
                except Exception:
                    if file_path.exists():
                        file_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="유효하지 않은 이미지 파일입니다."
                    )
            
            # 웹에서 접근 가능한 상대 경로 생성
            relative_path = f"/static/uploads/chat/{category}/{room_id}/{user_id}/{unique_filename}"
            
            return {
                "file_type": file_type,
                "file_url": relative_path,
                "file_name": file.filename,
                "file_size": file_size
            }
            
        except Exception as e:
            # 에러 발생 시 파일 삭제
            if file_path.exists():
                file_path.unlink()
            
            if isinstance(e, HTTPException):
                raise e
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"파일 저장 중 오류가 발생했습니다: {str(e)}"
                )
    
    @classmethod
    async def delete_chat_file(cls, file_url: str) -> bool:
        """채팅 파일 삭제"""
        try:
            # 상대 경로를 절대 경로로 변환
            if file_url.startswith('/static/'):
                file_url = file_url[1:]  # 앞의 '/' 제거
            
            full_path = Path(file_url)
            
            if full_path.exists():
                full_path.unlink()
                return True
            return False
            
        except Exception as e:
            print(f"파일 삭제 오류: {e}")
            return False
    
    @classmethod
    def get_file_info(cls, file_path: str) -> Dict[str, Any]:
        """파일 정보 조회"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            return {
                "file_name": path.name,
                "file_size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime
            }
        except Exception:
            return None
    
    @classmethod
    def is_image_file(cls, filename: str) -> bool:
        """이미지 파일인지 확인"""
        extension = Path(filename).suffix.lower()
        return extension in cls.ALLOWED_IMAGE_EXTENSIONS
    
    @classmethod
    def is_audio_file(cls, filename: str) -> bool:
        """오디오 파일인지 확인"""
        extension = Path(filename).suffix.lower()
        return extension in cls.ALLOWED_AUDIO_EXTENSIONS
    
    @classmethod
    def format_file_size(cls, size_bytes: int) -> str:
        """파일 크기를 읽기 쉬운 형태로 변환"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
