  # 대표 이미지 설정 API 가이드

  ## ✅ 새로 추가된 API

  ### PUT /api/users/{user_id}/images/{image_id}/primary

  프로필 이미지 중 하나를 대표 이미지로 설정합니다.

  ---

  ## 📋 API 상세

  ### 엔드포인트
  ```
  PUT /api/users/{user_id}/images/{image_id}/primary
  ```

  ### 권한
  - **본인만 가능**: 자신의 프로필 이미지만 대표로 설정할 수 있습니다
  - **인증 필요**: Bearer 토큰 필수

  ### 파라미터
  - `user_id` (path): 사용자 ID
  - `image_id` (path): 대표로 설정할 이미지 ID

  ---

  ## 🔥 동작 방식

  ### 1. 기존 대표 이미지 변경
  ```
  기존 대표 이미지 (is_primary=true) → is_primary=false로 변경
  선택한 이미지 (is_primary=false) → is_primary=true로 변경
  ```

  ### 2. 자동 처리
  - 한 사용자당 대표 이미지는 **단 1개만** 존재
  - 기존 대표 이미지는 자동으로 일반 이미지로 변경됨

  ### 3. 중복 방지
  - 이미 대표 이미지인 경우 변경하지 않고 메시지만 반환

  ---

  ## 📊 요청/응답 예시

  ### 요청 (Request)
  ```bash
  curl -X PUT http://localhost:8000/api/users/12/images/2/primary \
    -H "Authorization: Bearer {your_token}"
  ```

  ### 성공 응답 (200 OK)
  ```json
  {
    "message": "대표 이미지가 변경되었습니다.",
    "image": {
      "image_id": 2,
      "image_url": "/static/images/profiles/12/profile_12_2.jpg",
      "is_primary": true,
      "upload_order": 2
    }
  }
  ```

  ### 이미 대표 이미지인 경우 (200 OK)
  ```json
  {
    "message": "이미 대표 이미지로 설정되어 있습니다.",
    "image": {
      "image_id": 2,
      "image_url": "/static/images/profiles/12/profile_12_2.jpg",
      "is_primary": true
    }
  }
  ```

  ### 에러 응답

  #### 404 Not Found (이미지 없음)
  ```json
  {
    "detail": "이미지를 찾을 수 없습니다."
  }
  ```

  #### 403 Forbidden (권한 없음)
  ```json
  {
    "detail": "본인의 프로필 이미지만 변경할 수 있습니다."
  }
  ```

  ---

  ## 🎯 사용 시나리오

  ### 시나리오 1: 프로필 이미지 여러 개 업로드 후 선택

  1. **이미지 업로드**
  ```bash
  POST /api/users/12/images
  → 이미지 3개 업로드 (첫 번째가 자동으로 대표 이미지)
  ```

  2. **다른 이미지를 대표로 변경**
  ```bash
  PUT /api/users/12/images/2/primary
  → 2번 이미지가 대표 이미지가 됨
  ```

  3. **결과 확인**
  ```bash
  GET /api/users/12/profile
  → images 배열에서 image_id=2의 is_primary=true
  ```

  ### 시나리오 2: 프로필 화면에서 대표 이미지 변경

  ```
  사용자가 프로필 편집 화면에서
  → 여러 이미지 중 하나를 선택
  → "대표 이미지로 설정" 버튼 클릭
  → API 호출
  → 즉시 반영
  ```

  ---

  ## 💡 Flutter 연동 예시

  ### 1. API 호출 함수
  ```dart
  Future<Map<String, dynamic>> setPrimaryImage({
    required int userId,
    required int imageId,
  }) async {
    final response = await http.put(
      Uri.parse('$baseUrl/api/users/$userId/images/$imageId/primary'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('대표 이미지 설정 실패');
    }
  }
  ```

  ### 2. UI 구현 예시
  ```dart
  Widget buildImageGrid(List<dynamic> images) {
    return GridView.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: images.length,
      itemBuilder: (context, index) {
        final image = images[index];
        final isPrimary = image['is_primary'] ?? false;
        
        return GestureDetector(
          onLongPress: () async {
            // 대표 이미지로 설정
            final result = await showDialog<bool>(
              context: context,
              builder: (context) => AlertDialog(
                title: Text('대표 이미지 설정'),
                content: Text('이 이미지를 대표 이미지로 설정하시겠습니까?'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: Text('취소'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: Text('확인'),
                  ),
                ],
              ),
            );
            
            if (result == true) {
              await ApiService.setPrimaryImage(
                userId: currentUserId,
                imageId: image['image_id'],
              );
              
              // 프로필 다시 로드
              _loadProfile();
              
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('대표 이미지가 변경되었습니다')),
              );
            }
          },
          child: Stack(
            children: [
              // 이미지
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: isPrimary
                      ? Border.all(color: Colors.blue, width: 3)
                      : null,
                  image: DecorationImage(
                    image: NetworkImage(
                      '$baseUrl${image['image_url']}',
                    ),
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              // 대표 이미지 뱃지
              if (isPrimary)
                Positioned(
                  top: 4,
                  right: 4,
                  child: Container(
                    padding: EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: Colors.blue,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '대표',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
  ```

  ### 3. 간단한 버전 (버튼 방식)
  ```dart
  Widget buildImageItem(Map<String, dynamic> image) {
    final isPrimary = image['is_primary'] ?? false;
    
    return Column(
      children: [
        // 이미지
        Image.network('$baseUrl${image['image_url']}'),
        
        // 대표 이미지 설정 버튼
        if (!isPrimary)
          ElevatedButton(
            onPressed: () async {
              await ApiService.setPrimaryImage(
                userId: currentUserId,
                imageId: image['image_id'],
              );
              _loadProfile();
            },
            child: Text('대표로 설정'),
          )
        else
          Chip(
            label: Text('대표 이미지'),
            backgroundColor: Colors.blue,
          ),
      ],
    );
  }
  ```

  ---

  ## 🧪 테스트 방법

  ### 1. Swagger UI에서 테스트
  ```
  1. http://localhost:8000/docs 접속
  2. "Authorize" 버튼 클릭, 토큰 입력
  3. PUT /api/users/{user_id}/images/{image_id}/primary 찾기
  4. "Try it out" 클릭
  5. user_id, image_id 입력
  6. "Execute" 클릭
  ```

  ### 2. cURL로 테스트
  ```bash
  # 프로필 조회 (현재 대표 이미지 확인)
  curl -X GET http://localhost:8000/api/users/12/profile \
    -H "Authorization: Bearer {token}"

  # 대표 이미지 변경 (image_id=2로 변경)
  curl -X PUT http://localhost:8000/api/users/12/images/2/primary \
    -H "Authorization: Bearer {token}"

  # 다시 프로필 조회 (변경 확인)
  curl -X GET http://localhost:8000/api/users/12/profile \
    -H "Authorization: Bearer {token}"
  ```

  ### 3. 변경 확인
  ```json
  // 변경 전
  {
    "images": [
      {"image_id": 1, "is_primary": true},   // 기존 대표
      {"image_id": 2, "is_primary": false}
    ]
  }

  // API 호출: PUT /images/2/primary

  // 변경 후
  {
    "images": [
      {"image_id": 1, "is_primary": false},  // 일반 이미지로 변경
      {"image_id": 2, "is_primary": true}    // 새로운 대표
    ]
  }
  ```

  ---

  ## 📊 전체 프로필 이미지 API 목록

  ### 1. 이미지 업로드
  ```
  POST /api/users/{user_id}/images
  ```

  ### 2. 프로필 조회 (이미지 포함)
  ```
  GET /api/users/{user_id}/profile
  ```

  ### 3. 이미지만 조회
  ```
  GET /api/users/{user_id}/profile/images
  ```

  ### 4. 대표 이미지 설정 ⭐ NEW
  ```
  PUT /api/users/{user_id}/images/{image_id}/primary
  ```

  ### 5. 이미지 삭제
  ```
  DELETE /api/users/{user_id}/images/{image_id}
  ```

  ---

  ## ⚠️ 주의사항

  ### 1. 권한 확인
  - 반드시 **본인의 이미지**만 대표로 설정 가능
  - 다른 사용자의 이미지 변경 시 403 에러

  ### 2. 이미지 존재 확인
  - 존재하지 않는 image_id 사용 시 404 에러
  - user_id와 image_id가 일치하지 않으면 404 에러

  ### 3. 자동 처리
  - 기존 대표 이미지는 자동으로 일반 이미지로 변경
  - 별도 API 호출 불필요

  ### 4. 이미지 순서
  - `upload_order`는 변경되지 않음
  - 대표 이미지는 `is_primary` 필드로만 구분

  ---

  ## 💡 Best Practice

  ### 1. UI/UX 권장사항
  - 대표 이미지는 **파란색 테두리**나 **뱃지**로 표시
  - 길게 누르기(Long Press)로 대표 이미지 변경
  - 변경 시 확인 다이얼로그 표시
  - 변경 후 즉시 화면 새로고침

  ### 2. 에러 처리
  ```dart
  try {
    await ApiService.setPrimaryImage(
      userId: userId,
      imageId: imageId,
    );
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('대표 이미지가 변경되었습니다')),
    );
  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('대표 이미지 변경 실패: $e')),
    );
  }
  ```

  ### 3. 낙관적 UI 업데이트
  ```dart
  // API 호출 전에 UI 먼저 업데이트
  setState(() {
    for (var img in images) {
      img['is_primary'] = img['image_id'] == selectedImageId;
    }
  });

  // 그 다음 API 호출
  try {
    await ApiService.setPrimaryImage(...);
  } catch (e) {
    // 실패 시 UI 복구
    _loadProfile();
  }
  ```

  ---

  **작성일**: 2024년 1월 8일  
  **버전**: 1.0  
  **상태**: ✅ 구현 완료

