"""
테스트용 사용자 2명 생성
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def create_user(email, password, name):
    """사용자 생성"""
    try:
        # 1. 이메일 인증 코드 요청
        print(f"1. {email} 이메일 인증 코드 요청...")
        response = requests.post(
            f"{BASE_URL}/auth/send-verification-code",
            json={"email": email, "purpose": "register"}
        )
        print(f"   Status: {response.status_code}")
        
        # 2. 사용자 생성 (인증 코드 없이 - 개발 모드)
        print(f"2. {email} 사용자 생성...")
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name,
                "birth_date": "1995-01-01",
                "gender": "M",
                "nationality": "한국",
                "terms_agreed": True
            }
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"   ✅ 사용자 생성 성공! User ID: {data.get('user_id')}")
            return data
        else:
            print(f"   응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ 에러: {e}")
        return None

def login(email, password):
    """로그인"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {email} 로그인 성공")
            return data["access_token"]
        else:
            print(f"❌ 로그인 실패: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ 로그인 에러: {e}")
        return None

def main():
    print("\n" + "="*60)
    print("  테스트 사용자 생성")
    print("="*60 + "\n")
    
    # User A 생성
    print("📝 User A 생성 중...")
    user_a = create_user("testuser1@kbu.ac.kr", "test1234", "테스트유저A")
    print()
    
    # User B 생성
    print("📝 User B 생성 중...")
    user_b = create_user("testuser2@kbu.ac.kr", "test1234", "테스트유저B")
    print()
    
    if user_a and user_b:
        print("\n" + "="*60)
        print("  ✅ 테스트 사용자 생성 완료!")
        print("="*60)
        print(f"\nUser A:")
        print(f"  Email: testuser1@kbu.ac.kr")
        print(f"  Password: test1234")
        print(f"  Name: {user_a.get('name')}")
        print(f"  User ID: {user_a.get('user_id')}")
        
        print(f"\nUser B:")
        print(f"  Email: testuser2@kbu.ac.kr")
        print(f"  Password: test1234")
        print(f"  Name: {user_b.get('name')}")
        print(f"  User ID: {user_b.get('user_id')}")
        
        print("\n💡 test_matching_chat.py를 다음과 같이 수정하세요:")
        print("""
USER_A = {
    "email": "testuser1@kbu.ac.kr",
    "password": "test1234"
}

USER_B = {
    "email": "testuser2@kbu.ac.kr",
    "password": "test1234"
}
""")
    else:
        print("\n❌ 사용자 생성 실패")
        print("이미 존재하는 사용자일 수 있습니다.")
        print("\n로그인 테스트 중...")
        
        token_a = login("testuser1@kbu.ac.kr", "test1234")
        token_b = login("testuser2@kbu.ac.kr", "test1234")
        
        if token_a and token_b:
            print("\n✅ 기존 사용자로 로그인 가능!")
            print("test_matching_chat.py를 실행하세요.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러: {e}")
        import traceback
        traceback.print_exc()

