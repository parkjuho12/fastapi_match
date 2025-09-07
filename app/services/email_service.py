import os
import random
import string
import ssl
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from app.config.email_config import get_email_settings

# 이메일 설정 가져오기
email_settings = get_email_settings()
SMTP_SERVER = email_settings["smtp_server"]
SMTP_PORT = email_settings["smtp_port"]
SMTP_USER = email_settings["smtp_user"]
SMTP_PASSWORD = email_settings["smtp_password"]

class EmailService:
    
    @staticmethod
    def generate_verification_code() -> str:
        """6자리 랜덤 인증번호 생성"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def create_verification_email(recipient_email: str, verification_code: str, purpose: str = "password_reset") -> MIMEMultipart:
        """인증 이메일 생성"""
        message = MIMEMultipart("alternative")
        message["Subject"] = "경복대학교 매칭앱 - 인증번호"
        message["From"] = SMTP_USER
        message["To"] = recipient_email
        
        if purpose == "password_reset":
            html_content = f"""
            <html>
              <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                  <h2 style="color: #2c3e50;">경복대학교 매칭앱</h2>
                  <h3 style="color: #34495e;">비밀번호 재설정 인증번호</h3>
                  
                  <p>안녕하세요!</p>
                  <p>비밀번호 재설정을 위한 인증번호를 보내드립니다.</p>
                  
                  <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <h2 style="color: #e74c3c; font-size: 32px; margin: 0; letter-spacing: 8px;">
                      {verification_code}
                    </h2>
                  </div>
                  
                  <p><strong>주의사항:</strong></p>
                  <ul>
                    <li>이 인증번호는 <strong>10분간</strong> 유효합니다.</li>
                    <li>인증번호를 타인에게 공유하지 마세요.</li>
                    <li>본인이 요청하지 않았다면 이 이메일을 무시하세요.</li>
                  </ul>
                  
                  <hr style="margin: 30px 0; border: none; border-top: 1px solid #ecf0f1;">
                  <p style="color: #7f8c8d; font-size: 12px;">
                    이 이메일은 자동으로 발송된 메일입니다. 회신하지 마세요.<br>
                    경복대학교 매칭앱 관리팀
                  </p>
                </div>
              </body>
            </html>
            """
        else:
            html_content = f"""
            <html>
              <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                  <h2 style="color: #2c3e50;">경복대학교 매칭앱</h2>
                  <h3 style="color: #34495e;">이메일 인증번호</h3>
                  
                  <p>안녕하세요!</p>
                  <p>이메일 인증을 위한 인증번호를 보내드립니다.</p>
                  
                  <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <h2 style="color: #27ae60; font-size: 32px; margin: 0; letter-spacing: 8px;">
                      {verification_code}
                    </h2>
                  </div>
                  
                  <p><strong>주의사항:</strong></p>
                  <ul>
                    <li>이 인증번호는 <strong>10분간</strong> 유효합니다.</li>
                    <li>인증번호를 타인에게 공유하지 마세요.</li>
                  </ul>
                  
                  <hr style="margin: 30px 0; border: none; border-top: 1px solid #ecf0f1;">
                  <p style="color: #7f8c8d; font-size: 12px;">
                    이 이메일은 자동으로 발송된 메일입니다. 회신하지 마세요.<br>
                    경복대학교 매칭앱 관리팀
                  </p>
                </div>
              </body>
            </html>
            """
        
        part = MIMEText(html_content, "html")
        message.attach(part)
        
        return message
    
    @staticmethod
    async def send_verification_email(recipient_email: str, verification_code: str, purpose: str = "password_reset") -> bool:
        """인증 이메일 발송"""
        # 테스트 모드: 실제 이메일을 보내지 않고 콘솔에 출력
        test_mode = email_settings["test_mode"]
        
        if test_mode:
            print(f"\n{'='*50}")
            print(f"📧 실제 메일 발송 시뮬레이션")
            print(f"받는 사람: {recipient_email}")
            print(f"발송자: {SMTP_USER}")
            print(f"SMTP 서버: {SMTP_SERVER}:{SMTP_PORT}")
            print(f"목적: {purpose}")
            print(f"🔑 인증번호: {verification_code}")
            print(f"유효시간: 10분")
            print(f"")
            print(f"📬 {recipient_email}로 다음 내용의 메일이 발송됩니다:")
            print(f"제목: 경복대학교 매칭앱 - 인증번호")
            print(f"내용: 비밀번호 재설정을 위한 인증번호는 {verification_code}입니다.")
            print(f"{'='*50}\n")
            return True
        
        # 실제 이메일 발송 (프로덕션 모드)
        try:
            print(f"📧 실제 메일 발송 시도:")
            print(f"  SMTP 서버: {SMTP_SERVER}:{SMTP_PORT}")
            print(f"  발송자: {SMTP_USER}")
            print(f"  받는사람: {recipient_email}")
            print(f"  인증번호: {verification_code}")
            
            message = EmailService.create_verification_email(recipient_email, verification_code, purpose)
            
            # SSL 컨텍스트 설정 (인증서 검증 문제 해결)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # SMTP 연결 및 이메일 발송 (포트 465 SSL 직접 연결)
            print("  SMTP 서버 연결 중...")
            server = aiosmtplib.SMTP(hostname=SMTP_SERVER, port=SMTP_PORT, use_tls=True, tls_context=context)
            await server.connect()
            print("  Gmail 로그인 중...")
            await server.login(SMTP_USER, SMTP_PASSWORD)
            print("  메일 전송 중...")
            await server.send_message(message)
            await server.quit()
            
            print(f"✅ 인증 이메일 발송 성공: {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ 이메일 발송 실패: {e}")
            print(f"   에러 타입: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_expiry_time() -> datetime:
        """인증번호 만료 시간 반환 (현재시간 + 10분)"""
        return datetime.utcnow() + timedelta(minutes=10)
    
    @staticmethod
    def is_code_expired(expires_at: datetime) -> bool:
        """인증번호 만료 여부 확인"""
        return datetime.utcnow() > expires_at