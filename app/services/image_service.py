"""
이미지 업로드 및 처리 서비스
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import aiofiles

class ImageService:
    # 허용되는 이미지 형식
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    # 최대 파일 크기 (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 이미지 저장 디렉토리
    UPLOAD_DIR = Path("static/images/profiles")
    
    @classmethod
    def setup_directories(cls):
        """이미지 저장 디렉토리 생성"""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_image_file(cls, file: UploadFile) -> bool:
        """이미지 파일 검증"""
        # 파일 확장자 검증
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in cls.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 파일 형식입니다. 허용 형식: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        # 파일 크기 검증 (파일 크기가 제공되는 경우)
        if hasattr(file, 'size') and file.size and file.size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 크기가 너무 큽니다. 최대 크기: {cls.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        return True
    
    @classmethod
    def generate_unique_filename(cls, original_filename: str) -> str:
        """고유한 파일명 생성"""
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"
    
    @classmethod
    async def save_image(cls, file: UploadFile, user_id: int) -> tuple[str, str, int]:
        """
        이미지 파일 저장
        Returns: (file_path, original_filename, file_size)
        """
        # 디렉토리 생성
        cls.setup_directories()
        
        # 파일 검증
        cls.validate_image_file(file)
        
        # 고유 파일명 생성
        unique_filename = cls.generate_unique_filename(file.filename)
        
        # 사용자별 디렉토리 생성
        user_dir = cls.UPLOAD_DIR / str(user_id)
        user_dir.mkdir(exist_ok=True)
        
        # 파일 경로
        file_path = user_dir / unique_filename
        
        # 파일 저장
        file_size = 0
        try:
            # 파일 내용 읽기 및 저장
            content = await file.read()
            file_size = len(content)
            
            # 파일 크기 재검증
            if file_size > cls.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"파일 크기가 너무 큽니다. 최대 크기: {cls.MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            # 파일 저장
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # 이미지 검증 (PIL로 열어보기)
            try:
                with Image.open(file_path) as img:
                    img.verify()  # 이미지 파일인지 검증
            except Exception:
                # 검증 실패 시 파일 삭제
                if file_path.exists():
                    file_path.unlink()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="유효하지 않은 이미지 파일입니다."
                )
            
            # 상대 경로 반환 (웹에서 접근 가능한 경로)
            relative_path = f"/static/images/profiles/{user_id}/{unique_filename}"
            
            return relative_path, file.filename, file_size
            
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
    async def save_multiple_images(cls, files: List[UploadFile], user_id: int) -> List[tuple[str, str, int]]:
        """
        여러 이미지 파일 저장
        Returns: List of (file_path, original_filename, file_size)
        """
        if len(files) > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최대 6개의 이미지만 업로드할 수 있습니다."
            )
        
        results = []
        saved_files = []
        
        try:
            for file in files:
                if file.filename:  # 빈 파일이 아닌 경우만 처리
                    result = await cls.save_image(file, user_id)
                    results.append(result)
                    saved_files.append(result[0])
            
            return results
            
        except Exception as e:
            # 에러 발생 시 저장된 파일들 삭제
            await cls.delete_multiple_images(saved_files)
            raise e
    
    @classmethod
    async def delete_image(cls, file_path: str) -> bool:
        """이미지 파일 삭제"""
        try:
            # 상대 경로를 절대 경로로 변환
            if file_path.startswith('/static/'):
                file_path = file_path[1:]  # 앞의 '/' 제거
            
            full_path = Path(file_path)
            
            if full_path.exists():
                full_path.unlink()
                return True
            return False
            
        except Exception as e:
            print(f"이미지 삭제 오류: {e}")
            return False
    
    @classmethod
    async def delete_multiple_images(cls, file_paths: List[str]) -> int:
        """여러 이미지 파일 삭제"""
        deleted_count = 0
        
        for file_path in file_paths:
            if await cls.delete_image(file_path):
                deleted_count += 1
        
        return deleted_count
    
    @classmethod
    def get_image_url(cls, file_path: str, base_url: str = "") -> str:
        """이미지 URL 생성"""
        if file_path.startswith('/'):
            return f"{base_url}{file_path}"
        else:
            return f"{base_url}/{file_path}"
