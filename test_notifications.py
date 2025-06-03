#!/usr/bin/env python3
"""
SNS 알림 테스트 스크립트

사용법:
python test_notifications.py
"""

import os
import logging
from notification import notifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_notifications():
    """알림 기능 테스트"""
    
    # SNS 설정 확인
    sns_topic_arn = os.getenv("SNS_TOPIC_ARN")
    if not sns_topic_arn:
        print("⚠️ SNS_TOPIC_ARN 환경변수가 설정되지 않았습니다.")
        print("Lambda 배포 후 또는 로컬 테스트를 위해 SNS_TOPIC_ARN을 설정하세요.")
        print("배포된 토픽 ARN 확인 방법:")
        print("aws cloudformation describe-stacks --stack-name bitcoin-auto-trader-dev --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' --output text")
        return
    
    print(f"📡 SNS 토픽: {sns_topic_arn}")
    print("\n🧪 알림 기능 테스트를 시작합니다...\n")
    
    try:
        # 1. 봇 시작 알림 테스트
        print("1️⃣ 봇 시작 알림 테스트...")
        notifier.notify_bot_started()
        print("✅ 봇 시작 알림 발송 완료\n")
        
        # 2. 거래 실행 알림 테스트 (매수)
        print("2️⃣ 매수 알림 테스트...")
        notifier.notify_trade_executed("BUY", 45000.0, 0.001111, 50.0)
        print("✅ 매수 알림 발송 완료\n")
        
        # 3. 거래 실행 알림 테스트 (매도)
        print("3️⃣ 매도 알림 테스트...")
        notifier.notify_trade_executed("SELL", 46500.0, 0.001111, 100.0)
        print("✅ 매도 알림 발송 완료\n")
        
        # 4. 수익 실현 알림 테스트
        print("4️⃣ 수익 실현 알림 테스트...")
        notifier.notify_profit_achieved(45000.0, 46500.0, 1.5, 0.033)
        print("✅ 수익 실현 알림 발송 완료\n")
        
        # 5. 잔고 부족 알림 테스트
        print("5️⃣ 잔고 부족 알림 테스트...")
        notifier.notify_insufficient_balance(50.0, 25.0)
        print("✅ 잔고 부족 알림 발송 완료\n")
        
        # 6. 오류 알림 테스트
        print("6️⃣ 오류 알림 테스트...")
        notifier.notify_error("테스트 오류", "이것은 테스트용 오류 메시지입니다.", {
            "error_code": "TEST_001",
            "timestamp": "2024-01-01 12:00:00"
        })
        print("✅ 오류 알림 발송 완료\n")
        
        print("🎉 모든 알림 테스트가 완료되었습니다!")
        print("📧 이메일을 확인하여 알림이 정상적으로 도착했는지 확인하세요.")
        
    except Exception as e:
        print(f"❌ 알림 테스트 중 오류 발생: {e}")
        logger.error(f"알림 테스트 실패: {e}", exc_info=True)


if __name__ == "__main__":
    test_notifications() 