# 장소 추천 (Place) API 구현 완료

**작성일**: 2025-12-03  
**상태**: ✅ 구현 완료

---

## 📋 구현된 API 목록 (총 15개)

### 1. 장소 CRUD (5개)

#### 1.1 장소 목록 조회
```
GET /places/
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| page | int | N | 페이지 번호 (기본값: 1) |
| size | int | N | 페이지 크기 (기본값: 20) |
| category | string | N | 카테고리 필터 |
| sort | string | N | 정렬 (popular, latest, likes, rating) |
| q | string | N | 검색어 (제목, 주소) |

**응답**:
```json
{
  "places": [
    {
      "place_id": 1,
      "author_id": 10,
      "author_name": "홍길동",
      "title": "캠퍼스 스터디 카페",
      "address": "서울시 강남구 역삼동 123-45",
      "category": "카페",
      "image_url": "/static/images/places/1_abc.jpg",
      "view_count": 150,
      "like_count": 93,
      "review_count": 12,
      "avg_rating": 4.5,
      "is_liked": true,
      "created_at": "2025-12-03T10:00:00"
    }
  ],
  "total_count": 50,
  "page": 1,
  "size": 20
}
```

---

#### 1.2 장소 상세 조회
```
GET /places/{place_id}
```

**응답**:
```json
{
  "place_id": 1,
  "author_id": 10,
  "author_name": "홍길동",
  "title": "캠퍼스 스터디 카페",
  "content": "장소 소개 내용...",
  "address": "서울시 강남구 역삼동 123-45",
  "category": "카페",
  "images": [
    {
      "image_id": 1,
      "image_url": "/static/images/places/1_abc.jpg",
      "upload_order": 0
    }
  ],
  "view_count": 151,
  "like_count": 93,
  "review_count": 12,
  "avg_rating": 4.5,
  "is_liked": true,
  "created_at": "2025-12-03T10:00:00",
  "updated_at": "2025-12-03T10:00:00"
}
```

**Note**: 상세 조회 시 `view_count` 자동 증가

---

#### 1.3 장소 등록
```
POST /places/
```

**요청 본문**:
```json
{
  "title": "캠퍼스 스터디 카페",
  "content": "장소 소개 내용...",
  "address": "서울시 강남구 역삼동 123-45",
  "category": "카페"
}
```

---

#### 1.4 장소 수정
```
PUT /places/{place_id}
```

**권한**: 작성자 본인만

**요청 본문** (모든 필드 선택):
```json
{
  "title": "수정된 장소 이름",
  "content": "수정된 내용...",
  "address": "수정된 주소",
  "category": "스터디룸"
}
```

---

#### 1.5 장소 삭제
```
DELETE /places/{place_id}
```

**권한**: 작성자 본인만

**응답**:
```json
{
  "message": "장소가 삭제되었습니다."
}
```

---

### 2. 이미지 (2개)

#### 2.1 이미지 업로드
```
POST /places/{place_id}/images
```

**권한**: 작성자 본인만

**요청**: multipart/form-data
- `image`: 이미지 파일 (jpg, jpeg, png, webp)

**응답**:
```json
{
  "image_id": 1,
  "image_url": "/static/images/places/1_abc123.jpg",
  "upload_order": 0
}
```

---

#### 2.2 이미지 삭제
```
DELETE /places/{place_id}/images/{image_id}
```

**권한**: 작성자 본인만

**응답**:
```json
{
  "message": "이미지가 삭제되었습니다."
}
```

---

### 3. 좋아요 (1개)

#### 3.1 좋아요 토글
```
POST /places/{place_id}/like
```

**응답**:
```json
{
  "place_id": 1,
  "is_liked": true,
  "like_count": 94
}
```

---

### 4. 리뷰 (4개)

#### 4.1 리뷰 목록 조회
```
GET /places/{place_id}/reviews
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| page | int | N | 페이지 번호 (기본값: 1) |
| size | int | N | 페이지 크기 (기본값: 20) |
| sort | string | N | 정렬 (latest, rating_high, rating_low) |

**응답**:
```json
{
  "reviews": [
    {
      "review_id": 1,
      "place_id": 1,
      "author_id": 20,
      "author_name": "김철수",
      "author_profile_image": "/static/images/profiles/20/profile.jpg",
      "rating": 5,
      "content": "조용하고 자리 간격이 넓어요.",
      "visit_date": "2025-12-01",
      "created_at": "2025-12-02T15:30:00",
      "updated_at": null
    }
  ],
  "total_count": 12,
  "avg_rating": 4.5,
  "rating_distribution": {
    "5": 6,
    "4": 4,
    "3": 2,
    "2": 0,
    "1": 0
  },
  "page": 1,
  "size": 20
}
```

---

#### 4.2 리뷰 작성
```
POST /places/{place_id}/reviews
```

**제한**: 본인이 등록한 장소에는 리뷰 불가

**요청 본문**:
```json
{
  "rating": 5,
  "content": "조용하고 자리 간격이 넓어요.",
  "visit_date": "2025-12-01"
}
```

---

#### 4.3 리뷰 수정
```
PUT /places/{place_id}/reviews/{review_id}
```

**권한**: 작성자 본인만

**요청 본문**:
```json
{
  "rating": 4,
  "content": "수정된 리뷰 내용"
}
```

---

#### 4.4 리뷰 삭제
```
DELETE /places/{place_id}/reviews/{review_id}
```

**권한**: 작성자 본인만

**응답**:
```json
{
  "message": "리뷰가 삭제되었습니다."
}
```

---

### 5. 내 목록 (3개)

#### 5.1 내가 등록한 장소 목록
```
GET /users/me/places
```

---

#### 5.2 내가 좋아요한 장소 목록
```
GET /users/me/liked-places
```

---

#### 5.3 내가 작성한 리뷰 목록
```
GET /users/me/place-reviews
```

**응답**:
```json
{
  "reviews": [
    {
      "review_id": 1,
      "place_id": 1,
      "place_title": "캠퍼스 스터디 카페",
      "rating": 5,
      "content": "조용하고 좋아요",
      "visit_date": "2025-12-01",
      "created_at": "2025-12-02T15:30:00"
    }
  ],
  "total_count": 3
}
```

---

## 📊 카테고리 목록

| 값 | 설명 |
|---|------|
| `카페` | 카페, 커피숍 |
| `스터디룸` | 독서실, 스터디카페, 자습실 |
| `운동시설` | 헬스장, 체육관, 수영장 |
| `도서관` | 도서관, 열람실 |
| `공원` | 공원, 운동장, 야외 공간 |
| `라운지` | 학교 라운지, 휴게실 |
| `기타` | 기타 장소 |

---

## 🔐 권한

| API | 권한 |
|-----|------|
| 목록/상세 조회 | 로그인 사용자 |
| 장소 등록 | 로그인 사용자 |
| 장소 수정/삭제 | 작성자 본인만 |
| 이미지 업로드/삭제 | 작성자 본인만 |
| 좋아요 | 로그인 사용자 |
| 리뷰 작성 | 로그인 사용자 (본인 장소 제외) |
| 리뷰 수정/삭제 | 작성자 본인만 |

---

## 🗄️ DB 테이블 생성 SQL

```sql
-- 장소 테이블
CREATE TABLE places (
    place_id INT PRIMARY KEY AUTO_INCREMENT,
    author_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    address VARCHAR(500),
    category VARCHAR(50) NOT NULL DEFAULT '기타',
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    review_count INT DEFAULT 0,
    avg_rating FLOAT DEFAULT 0.0,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(user_id)
);

-- 장소 이미지 테이블
CREATE TABLE place_images (
    image_id INT PRIMARY KEY AUTO_INCREMENT,
    place_id INT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    upload_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);

-- 장소 좋아요 테이블
CREATE TABLE place_likes (
    like_id INT PRIMARY KEY AUTO_INCREMENT,
    place_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_place_like (place_id, user_id),
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 장소 리뷰 테이블
CREATE TABLE place_reviews (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    place_id INT NOT NULL,
    author_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    content TEXT NOT NULL,
    visit_date DATE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(user_id)
);
```

---

## 🔑 인증

모든 API는 JWT 토큰 인증 필요:

```
Authorization: Bearer {access_token}
```

---

**마지막 업데이트**: 2025-12-03

