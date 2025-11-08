"""
데이터베이스에 직접 테스트 사용자 추가
"""
from app.models.database import SessionLocal
from app.models.models import User
from app.auth.security import generate_salt, hash_password_with_salt
from datetime import date

def create_test_users():
    db = SessionLocal()
    try:
        # User A
        email_a = "testuser1@kbu.ac.kr"
        existing_a = db.query(User).filter(User.email == email_a).first()   
        
        if not existing_a:
            salt_a = generate_salt()
            password_hash_a = hash_password_with_salt("test1234", salt_a)
            
            user_a = User(
                email=email_a,
                password_hash=password_hash_a,
                salt=salt_a,
                name="테스트유저A",
                birth_date=date(1995, 1, 1),
                gender="M",
                nationality="한국",
                terms_agreed=True
            )
            db.add(user_a)
            print(f"✅ User A 생성: {email_a}")
        else:
            print(f"ℹ️  User A 이미 존재: {email_a}")
            user_a = existing_a
        
        # User B
        email_b = "testuser2@kbu.ac.kr"
        existing_b = db.query(User).filter(User.email == email_b).first()
        
        if not existing_b:
            salt_b = generate_salt()
            password_hash_b = hash_password_with_salt("test1234", salt_b)
            
            user_b = User(
                email=email_b,
                password_hash=password_hash_b,
                salt=salt_b,
                name="테스트유저B",
                birth_date=date(1995, 1, 1),
                gender="F",
                nationality="한국",
                terms_agreed=True
            )
            db.add(user_b)
            print(f"✅ User B 생성: {email_b}")
        else:
            print(f"ℹ️  User B 이미 존재: {email_b}")
            user_b = existing_b
        
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        
        print("\n" + "="*60)
        print("  ✅ 테스트 사용자 준비 완료!")
        print("="*60)
        print(f"\nUser A:")
        print(f"  Email: {user_a.email}")
        print(f"  Password: test1234")
        print(f"  Name: {user_a.name}")
        print(f"  User ID: {user_a.user_id}")
        
        print(f"\nUser B:")
        print(f"  Email: {user_b.email}")
        print(f"  Password: test1234")
        print(f"  Name: {user_b.name}")
        print(f"  User ID: {user_b.user_id}")
        
        print("\n💡 이제 test_matching_chat.py를 실행하세요!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()

