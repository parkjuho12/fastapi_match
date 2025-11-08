# 프로필 이미지 API 가이드

## ✅ 이미 구현된 프로필 이미지 시스템

프로필 이미지 시스템이 **이미 완벽하게 구현**되어 있습니다!

---

## 📊 데이터베이스 모델

### UserImage 테이블
```sql
CREATE TABLE user_images (
    image_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    upload_order INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_image_order (user_id, upload_order),
    INDEX idx_user_primary (user_id, is_primary)
);
```

**필드 설명**:
- `image_id`: 이미지 고유 ID
- `user_id`: 사용자 ID
- `image_url`: 이미지 파일 경로 (예: `/static/images/profiles/10/profile_10_1.jpg`)
- `is_primary`: 대표 이미지 여부 (true/false)
- `upload_order`: 업로드 순서 (1-6)
- `file_name`: 원본 파일명
- `file_size`: 파일 크기 (bytes)

---

## 🔥 프로필 이미지 API (3개)

### 1. 프로필 조회 (이미지 포함)
```
GET /api/users/{user_id}/profile
```

**권한**: 로그인한 사용자

**응답**: `UserProfileResponse`
```json
{
  "profile_id": 1,
  "user_id": 10,
  "friend_type": "친목",
  "department": "컴퓨터공학과",
  "student_status": "재학",
  "smoking": "비흡연",
  "drinking": "가끔",
  "religion": "무교",
  "mbti": "ENFP",
  "personality_keywords": "[\"밝은\", \"활발한\"]",
  "interest_keywords": "[\"운동\", \"영화\"]",
  "friend_style_keywords": "[\"편한\", \"솔직한\"]",
  "onboarding_completed": true,
  "onboarding_completed_at": "2024-01-08T10:00:00",
  "created_at": "2024-01-01T09:00:00",
  "updated_at": "2024-01-08T10:00:00",
  "keywords": [
    {
      "keyword_id": 1,
      "user_id": 10,
      "keyword_category": "personality",
      "keyword_value": "밝은",
      "keyword_order": 1
    }
  ],
  "images": [
    {
      "image_id": 1,
      "image_url": "/static/images/profiles/10/profile_10_1.jpg",
      "is_primary": true,
      "upload_order": 1,
      "file_name": "my_photo.jpg",
      "file_size": 204800,
      "created_at": "2024-01-01T09:00:00"
    },
    {
      "image_id": 2,
      "image_url": "/static/images/profiles/10/profile_10_2.jpg",
      "is_primary": false,
      "upload_order": 2,
      "file_name": "my_photo2.jpg",
      "file_size": 150000,
      "created_at": "2024-01-01T09:01:00"
    }
  ]
}
```

**특징**:
- 프로필 정보 + 키워드 + **이미지 목록** 모두 포함
- 이미지는 `upload_order` 순서대로 정렬
- `is_primary`로 대표 이미지 구분 가능

---

### 2. 프로필 이미지 업로드
```
POST /api/users/{user_id}/images
```

**권한**: 본인만 가능

**요청**: `multipart/form-data`
```
Content-Type: multipart/form-data

files: [파일1, 파일2, ...]
is_primary: true (첫 번째 이미지만)
```

**응답**: `ImageUploadResponse`
```json
{
  "message": "이미지 업로드 성공",
  "uploaded_images": [
    {
      "image_id": 1,
      "image_url": "/static/images/profiles/10/profile_10_1.jpg",
      "is_primary": true,
      "upload_order": 1,
      "file_name": "photo.jpg",
      "file_size": 204800,
      "created_at": "2024-01-08T10:00:00"
    }
  ],
  "total_count": 1
}
```

**제한사항**:
- 최대 6개까지 업로드 가능
- 파일 형식: JPG, JPEG, PNG
- 파일 크기: 최대 5MB
- 자동으로 첫 번째 이미지가 대표 이미지로 설정

**저장 경로**:
```
/static/images/profiles/{user_id}/profile_{user_id}_{order}.jpg
```

---

### 3. 프로필 이미지 삭제
```
DELETE /api/users/{user_id}/images/{image_id}
```

**권한**: 본인만 가능

**응답**:
```json
{
  "message": "이미지가 삭제되었습니다."
}
```

**특징**:
- 실제 파일도 함께 삭제 (물리적 삭제)
- 대표 이미지를 삭제하면 다음 순서 이미지가 자동으로 대표 이미지가 됨
- 업로드 순서(`upload_order`) 자동 재정렬

---

## 🔍 프로필 이미지 목록만 조회

### 별도 API 추가 필요? (선택사항)
현재는 `GET /api/users/{user_id}/profile`에 이미지가 포함되어 있습니다.

만약 **이미지만 별도로 조회**하고 싶다면:
```
GET /api/users/{user_id}/images
```

이 API를 추가할 수 있습니다. 필요하신가요?

---

## 💡 Flutter 연동 예시

### 1. 프로필 이미지 조회
```dart
Future<void> loadProfileImages() async {
  final response = await ApiService.getUserProfile(userId: currentUserId);
  
  setState(() {
    profileImages = response['images'];
    primaryImage = profileImages.firstWhere(
      (img) => img['is_primary'] == true,
      orElse: () => profileImages.isNotEmpty ? profileImages[0] : null,
    );
  });
}
```

### 2. 이미지 표시
```dart
Widget buildProfileImage() {
  if (primaryImage != null) {
    return CircleAvatar(
      radius: 50,
      backgroundImage: NetworkImage(
        'http://your-server.com${primaryImage['image_url']}'
      ),
    );
  } else {
    return CircleAvatar(
      radius: 50,
      child: Icon(Icons.person, size: 50),
    );
  }
}
```

### 3. 이미지 업로드
```dart
Future<void> uploadProfileImage(File imageFile) async {
  final formData = FormData();
  formData.files.add(
    MapEntry(
      'files',
      await MultipartFile.fromFile(
        imageFile.path,
        filename: 'profile.jpg',
      ),
    ),
  );
  
  await ApiService.uploadProfileImages(
    userId: currentUserId,
    formData: formData,
  );
  
  loadProfileImages(); // 업로드 후 새로고침
}
```

### 4. 이미지 삭제
```dart
Future<void> deleteProfileImage(int imageId) async {
  await ApiService.deleteProfileImage(
    userId: currentUserId,
    imageId: imageId,
  );
  
  loadProfileImages(); // 삭제 후 새로고침
}
```

---

## 📋 전체 이미지 관련 API 목록

### 프로필 이미지
1. ✅ `GET /api/users/{user_id}/profile` - 프로필 조회 (이미지 포함)
2. ✅ `POST /api/users/{user_id}/images` - 이미지 업로드
3. ✅ `DELETE /api/users/{user_id}/images/{image_id}` - 이미지 삭제

### 그룹 갤러리 이미지
4. ✅ `POST /groups/{group_id}/gallery/` - 갤러리 업로드
5. ✅ `GET /groups/{group_id}/gallery/` - 갤러리 목록
6. ✅ `DELETE /groups/{group_id}/gallery/{image_id}` - 갤러리 삭제

---

## 🧪 테스트 예시

### 1. 프로필 조회 (이미지 포함)
```bash
curl -X GET http://localhost:8000/api/users/10/profile \
  -H "Authorization: Bearer {token}"
```

### 2. 이미지 업로드
```bash
curl -X POST http://localhost:8000/api/users/10/images \
  -H "Authorization: Bearer {token}" \
  -F "files=@/path/to/photo1.jpg" \
  -F "files=@/path/to/photo2.jpg"
```

### 3. 이미지 삭제
```bash
curl -X DELETE http://localhost:8000/api/users/10/images/1 \
  -H "Authorization: Bearer {token}"
```

---

## ✅ 구현 완료 사항

- ✅ 데이터베이스 테이블 (`user_images`)
- ✅ 이미지 업로드 API (최대 6개)
- ✅ 이미지 삭제 API (물리적 삭제)
- ✅ 프로필 조회 시 이미지 포함
- ✅ 대표 이미지 자동 설정
- ✅ 파일 크기/형식 검증
- ✅ 업로드 순서 관리

---

## 🔧 필요 시 추가 가능한 기능

### 선택사항 1: 이미지만 조회하는 API
```
GET /api/users/{user_id}/images
```

### 선택사항 2: 대표 이미지 변경 API
```
PUT /api/users/{user_id}/images/{image_id}/primary
```

### 선택사항 3: 이미지 순서 변경 API
```
PUT /api/users/{user_id}/images/reorder
```

이 중에서 필요하신 기능이 있으신가요?

---

## 📝 정리

**프로필 이미지 시스템은 이미 완전히 구현되어 있습니다!**

1. ✅ 데이터베이스 모델: `UserImage`
2. ✅ API: 업로드, 삭제, 조회 (프로필에 포함)
3. ✅ 스키마: `UserImageResponse`
4. ✅ 파일 저장: `/static/images/profiles/{user_id}/`

**Flutter에서 해야 할 일**:
1. `GET /api/users/{user_id}/profile` API 호출
2. 응답의 `images` 배열 사용
3. `image_url`로 이미지 표시
4. `is_primary`로 대표 이미지 구분

---

**작성일**: 2024년 1월 8일  
**버전**: 1.0  
**상태**: ✅ 완전히 구현됨

