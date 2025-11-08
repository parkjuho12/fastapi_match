# 프로필 조회 API 최종 수정 완료 ✅

## 🐛 발생한 에러

```
NameError: name 'UserKeyword' is not defined
```

### 에러 발생 위치
```python
keywords = db.query(UserKeyword).filter(UserKeyword.user_id == user_id).all()
```

---

## 🔍 원인 분석

### 잘못된 가정
코드에서 `UserKeyword` 테이블이 존재한다고 가정했으나, **실제로는 존재하지 않음**

### 실제 데이터베이스 구조

```python
class UserProfile(Base):
    # ... 다른 필드들 ...
    
    # 키워드 필드들 (JSON 형태로 저장)
    personality_keywords = Column(String(1000), nullable=True)  # 성격 키워드 (JSON 배열)
    interest_keywords = Column(String(1000), nullable=True)     # 관심사 키워드 (JSON 배열)
    friend_style_keywords = Column(String(1000), nullable=True) # 친구 스타일 키워드 (JSON 배열)
```

**키포인트**:
- ❌ 별도의 `UserKeyword` 테이블 없음
- ✅ 키워드는 `UserProfile` 테이블에 JSON 문자열로 저장됨
- ✅ 3가지 타입: `personality_keywords`, `interest_keywords`, `friend_style_keywords`

---

## ✅ 최종 수정 코드

```python
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
        images = db.query(UserImage).filter(
            UserImage.user_id == user_id
        ).order_by(UserImage.upload_order).all()
        
        # 명시적으로 응답 생성
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
            personality_keywords=profile.personality_keywords,  # JSON 문자열
            interest_keywords=profile.interest_keywords,        # JSON 문자열
            friend_style_keywords=profile.friend_style_keywords,# JSON 문자열
            onboarding_completed=profile.onboarding_completed,
            onboarding_completed_at=profile.onboarding_completed_at,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            keywords=[],  # 빈 배열 (키워드는 JSON 필드로 제공됨)
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
```

### 변경 사항
1. ❌ 제거: `db.query(UserKeyword)` (존재하지 않는 테이블)
2. ✅ 유지: `personality_keywords`, `interest_keywords`, `friend_style_keywords` (JSON 문자열)
3. ✅ 추가: `keywords=[]` (빈 배열로 반환)

---

## 📊 API 응답 구조

### 성공 응답 (200 OK)
```json
{
  "profile_id": 1,
  "user_id": 12,
  "friend_type": "친목",
  "department": "컴퓨터공학과",
  "student_status": "재학",
  "smoking": "비흡연",
  "drinking": "가끔",
  "religion": "무교",
  "mbti": "ENFP",
  "personality_keywords": "[\"밝은\", \"활발한\", \"긍정적인\"]",
  "interest_keywords": "[\"운동\", \"영화\", \"음악\"]",
  "friend_style_keywords": "[\"편한\", \"솔직한\", \"유머러스한\"]",
  "onboarding_completed": true,
  "onboarding_completed_at": "2024-01-08T10:00:00",
  "created_at": "2024-01-01T09:00:00",
  "updated_at": "2024-01-08T10:00:00",
  "keywords": [],
  "images": [
    {
      "image_id": 1,
      "image_url": "/static/images/profiles/12/profile_12_1.jpg",
      "is_primary": true,
      "upload_order": 1,
      "file_name": "profile.jpg",
      "file_size": 204800,
      "created_at": "2024-01-01T09:00:00"
    }
  ]
}
```

### 주요 포인트
- ✅ `personality_keywords`, `interest_keywords`, `friend_style_keywords`: JSON 문자열로 제공
- ✅ `keywords`: 빈 배열 (레거시 필드, 사용하지 않음)
- ✅ `images`: 프로필 이미지 배열 (순서대로 정렬)

---

## 🧠 키워드 데이터 구조 이해

### JSON 문자열 형태
```json
"[\"밝은\", \"활발한\", \"긍정적인\"]"
```

### Flutter에서 파싱 방법
```dart
import 'dart:convert';

// API 응답 받기
final response = await ApiService.getUserProfile(userId: userId);

// JSON 문자열을 List로 파싱
List<String> personalityKeywords = [];
if (response['personality_keywords'] != null) {
  personalityKeywords = List<String>.from(
    jsonDecode(response['personality_keywords'])
  );
}

// 결과: ["밝은", "활발한", "긍정적인"]
print(personalityKeywords);
```

---

## ✅ 테스트 결과

### 서버 로그
```
INFO:     192.168.219.140:52881 - "GET /api/users/12/profile HTTP/1.1" 200 OK
```

### 예상 결과
- ✅ 200 OK: 프로필 정보 + 이미지 반환
- ✅ `keywords`: 빈 배열
- ✅ `personality_keywords`, `interest_keywords`, `friend_style_keywords`: JSON 문자열
- ❌ 500 에러: 발생하지 않음

---

## 🔧 Flutter 연동 가이드

### 1. 프로필 조회
```dart
Future<Map<String, dynamic>> loadUserProfile(int userId) async {
  final response = await ApiService.getUserProfile(userId: userId);
  return response;
}
```

### 2. 키워드 파싱
```dart
List<String> parseKeywords(String? jsonString) {
  if (jsonString == null || jsonString.isEmpty) {
    return [];
  }
  
  try {
    return List<String>.from(jsonDecode(jsonString));
  } catch (e) {
    print('키워드 파싱 에러: $e');
    return [];
  }
}

// 사용 예시
final profile = await loadUserProfile(12);
final personalityKeywords = parseKeywords(profile['personality_keywords']);
final interestKeywords = parseKeywords(profile['interest_keywords']);
final friendStyleKeywords = parseKeywords(profile['friend_style_keywords']);
```

### 3. 이미지 표시
```dart
Widget buildProfileImage(Map<String, dynamic> profile) {
  final images = profile['images'] as List?;
  
  if (images == null || images.isEmpty) {
    return CircleAvatar(
      radius: 50,
      child: Icon(Icons.person, size: 50),
    );
  }
  
  // 대표 이미지 찾기
  final primaryImage = images.firstWhere(
    (img) => img['is_primary'] == true,
    orElse: () => images[0],
  );
  
  return CircleAvatar(
    radius: 50,
    backgroundImage: NetworkImage(
      'http://your-server.com${primaryImage['image_url']}'
    ),
  );
}
```

---

## 📝 체크리스트

- [x] `UserKeyword` 테이블 미존재 확인
- [x] 키워드가 JSON 형태로 저장됨 확인
- [x] `keywords=[]` 빈 배열 반환으로 수정
- [x] 이미지 조회 로직 유지
- [x] 서버 재시작
- [ ] API 테스트 필요
- [ ] Flutter 앱에서 확인 필요

---

## 🎯 정리

### 에러 원인
- `UserKeyword` 테이블이 존재하지 않는데 조회하려고 시도
- Import도 되지 않은 클래스 사용

### 해결 방법
- `keywords=[]` 빈 배열 반환
- 키워드는 JSON 문자열 필드로 제공 (`personality_keywords` 등)

### 데이터 구조
```
UserProfile:
  ├─ personality_keywords: "[\"밝은\", \"활발한\"]"  (JSON 문자열)
  ├─ interest_keywords: "[\"운동\", \"영화\"]"      (JSON 문자열)
  ├─ friend_style_keywords: "[\"편한\", \"솔직한\"]" (JSON 문자열)
  └─ images: [...]                                 (UserImage 배열)
```

---

**수정일**: 2024년 1월 8일  
**버전**: 2.0  
**상태**: ✅ 최종 수정 완료, 테스트 대기

