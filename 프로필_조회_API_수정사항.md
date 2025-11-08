# 프로필 조회 API 500 에러 수정 완료

## 🐛 문제 원인

### GET /api/users/{user_id}/profile 엔드포인트에서 500 에러 발생

**원인**: SQLAlchemy 객체의 `__dict__` 사용 시 내부 속성 포함
```python
# 기존 코드 (문제)
response_data = profile.__dict__.copy()  # ❌ _sa_instance_state 등 내부 속성 포함
response_data['keywords'] = keywords
response_data['images'] = images
return UserProfileResponse(**response_data)
```

**문제점**:
1. `profile.__dict__`에는 SQLAlchemy 내부 속성(`_sa_instance_state` 등)이 포함됨
2. 이 내부 속성들이 Pydantic 모델 생성 시 충돌을 일으킴
3. 결과적으로 500 Internal Server Error 발생

---

## ✅ 수정 내용

### 명시적으로 필드 지정하여 응답 생성

```python
# 수정된 코드 (해결)
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
    keywords=[UserKeywordResponse(
        keyword_id=k.keyword_id,
        user_id=k.user_id,
        keyword_category=k.keyword_category,
        keyword_value=k.keyword_value,
        keyword_order=k.keyword_order
    ) for k in keywords],
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

---

## 🎯 수정 효과

### 1. 안전한 데이터 변환
- SQLAlchemy 내부 속성 제외
- 필요한 필드만 명시적으로 지정
- Pydantic 검증 통과

### 2. 이미지 정렬 추가
```python
images = db.query(UserImage).filter(
    UserImage.user_id == user_id
).order_by(UserImage.upload_order).all()  # ✅ 순서대로 정렬
```

### 3. 명확한 타입 변환
- 각 관련 객체를 명시적으로 Response 모델로 변환
- 타입 안정성 보장

---

## 📊 API 응답 예시

### 성공 응답 (200 OK)
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
    }
  ]
}
```

### 프로필 없음 (404 Not Found)
```json
{
  "detail": "프로필을 찾을 수 없습니다."
}
```

---

## 🧪 테스트 방법

### 1. 서버 재시작
```bash
cd '/Users/bagjuho/Desktop/매칭 앱(fast api)'
lsof -ti:8000 | xargs kill -9
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. API 테스트
```bash
# 프로필 조회
curl -X GET http://localhost:8000/api/users/10/profile \
  -H "Authorization: Bearer {your_token}"
```

### 3. 예상 결과
- ✅ 200 OK: 프로필 정보 + 키워드 + 이미지 반환
- ✅ 404 Not Found: 프로필 없음
- ❌ 500 에러: 발생하지 않아야 함

---

## 🔍 다른 유사 API 확인 결과

### 정상 작동 중인 API
1. ✅ `GET /api/users/onboarding/profile` - dictionary 반환 (문제 없음)
2. ✅ `GET /api/users/{user_id}/onboarding/profile` - dictionary 반환 (문제 없음)

이 API들은 Pydantic 모델을 사용하지 않고 dictionary를 직접 반환하므로 문제 없습니다.

---

## 💡 교훈 및 Best Practice

### ❌ 피해야 할 패턴
```python
# SQLAlchemy 객체의 __dict__ 직접 사용
response_data = model.__dict__.copy()
return PydanticModel(**response_data)
```

### ✅ 권장 패턴

**패턴 1: 명시적 필드 지정**
```python
return PydanticModel(
    field1=model.field1,
    field2=model.field2,
    # ... 모든 필드 명시
)
```

**패턴 2: from_attributes 사용 (단순한 경우)**
```python
class MyResponse(BaseModel):
    model_config = {"from_attributes": True}

# 단순히 SQLAlchemy 객체 전달 (관계 없는 경우)
return MyResponse.model_validate(model)
```

**패턴 3: dictionary 직접 반환**
```python
return {
    "field1": model.field1,
    "field2": model.field2
}
```

---

## 📝 체크리스트

- [x] 문제 원인 파악 (SQLAlchemy __dict__ 사용)
- [x] 코드 수정 (명시적 필드 지정)
- [x] 이미지 정렬 추가 (upload_order)
- [x] 타입 안정성 확보
- [ ] 서버 재시작 필요
- [ ] API 테스트 필요
- [ ] Flutter 앱에서 확인 필요

---

## 🚀 다음 단계

1. **서버 재시작**
   ```bash
   lsof -ti:8000 | xargs kill -9
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **API 테스트**
   - Postman/Thunder Client로 테스트
   - 응답 구조 확인

3. **Flutter 앱 연동**
   - `ApiService.getUserProfile()` 호출
   - `images` 배열 사용
   - 이미지 표시

---

**수정일**: 2024년 1월 8일  
**버전**: 1.0  
**상태**: ✅ 수정 완료, 테스트 대기

