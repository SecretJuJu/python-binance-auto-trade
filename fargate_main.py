#!/usr/bin/env python3
"""
AWS Fargate에서 실행되는 비트코인 자동거래 봇
10분마다 EventBridge에 의해 트리거됨
"""

import logging
import os
import sys
import traceback
from datetime import datetime

from notification import notifier
from state_store import state_store
from trade import TradingBot

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 Bitcoin Trading Bot (Fargate) started")
        logger.info(f"⏰ Execution time: {datetime.now().isoformat()}")

        # 환경 변수 확인
        required_env_vars = ["BINANCE_API_KEY", "BINANCE_SECRET"]
        for var in required_env_vars:
            if not os.getenv(var):
                raise ValueError(f"Required environment variable {var} is not set")

        # 거래 봇 초기화
        bot = TradingBot()
        logger.info("✅ Trading bot initialized successfully")

        # 현재 상태 로드
        current_state = state_store.load_state()
        logger.info(f"📊 Current state loaded: {current_state}")

        # 거래 전략 실행
        logger.info("🔄 Executing trading strategy...")
        updated_state = bot.execute_strategy(current_state)

        # 상태 저장
        state_store.save_state(updated_state)
        logger.info(f"💾 State saved: {updated_state}")

        # 성공 알림 (선택적)
        if os.getenv("NOTIFY_ON_SUCCESS", "false").lower() == "true":
            notifier.notify_bot_status(
                "Bot 실행 완료",
                f"거래 봇이 성공적으로 실행되었습니다.\n"
                f"실행 시간: {datetime.now().isoformat()}\n"
                f"다음 실행: 10분 후",
            )

        logger.info("✅ Trading bot execution completed successfully")
        return 0

    except Exception as e:
        error_msg = f"❌ Trading bot execution failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")

        # 오류 알림
        try:
            notifier.notify_error(
                "Fargate Bot 실행 오류",
                f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}",
                {"execution_time": datetime.now().isoformat()},
            )
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")

        return 1

    finally:
        logger.info("🏁 Bitcoin Trading Bot (Fargate) finished")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 