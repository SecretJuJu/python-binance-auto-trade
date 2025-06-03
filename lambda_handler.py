import json
import logging
from datetime import datetime

from state_store import StateStore
from trade import TradingBot
from notification import notifier

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(event, context):
    """
    Lambda 메인 핸들러
    매 시간마다 EventBridge에 의해 트리거됨
    """
    try:
        logger.info(f"Auto trading started at {datetime.now()}")

        # 트레이딩 봇 초기화
        trading_bot = TradingBot()
        state_store = StateStore()

        # 현재 거래 상태 조회
        current_state = state_store.load_state()
        logger.info(f"Current trading state: {current_state}")

        # 트레이딩 실행
        result = trading_bot.execute_strategy(current_state)

        # 결과 저장
        if result.get("state_changed", False):
            state_store.save_state(result["new_state"])
            logger.info(f"Trading state updated: {result['new_state']}")

        # 실행 결과 반환
        response = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": result.get("action", "NO_ACTION"),
                    "message": result.get("message", "Strategy executed successfully"),
                    "current_balance": result.get("current_balance", 0),
                    "current_position": result.get("current_position", None),
                },
                ensure_ascii=False,
            ),
        }

        logger.info(f"Trading execution completed: {result.get('action', 'NO_ACTION')}")
        return response

    except Exception as e:
        error_msg = f"Trading execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # 전역 에러 알림 발송
        notifier.notify_error("Lambda 실행 실패", error_msg, {
            "timestamp": datetime.now().isoformat(),
            "event": str(event)
        })

        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": error_msg, "timestamp": datetime.now().isoformat()}
            ),
        }
