import logging
import os
from datetime import datetime
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

from config_loader import config_loader

logger = logging.getLogger(__name__)


class TradingNotifier:
    """거래 알림 관리 클래스"""

    def __init__(self):
        self.sns_client = boto3.client("sns", region_name="ap-northeast-2")
        aws_config = config_loader.get_aws_config()
        self.topic_arn = os.getenv("SNS_TOPIC_ARN")
        self.enabled = aws_config.get("enable_notifications", True)

        if not self.topic_arn and self.enabled:
            logger.warning("SNS_TOPIC_ARN 환경변수가 설정되지 않았습니다. 알림이 비활성화됩니다.")
            self.enabled = False

        if self.enabled and self.topic_arn:
            logger.info(f"SNS 알림 활성화됨 - 토픽: {self.topic_arn}")

    def send_notification(
        self, subject: str, message: str, data: Optional[Dict] = None
    ):
        """SNS 알림 발송"""
        if not self.enabled or not self.topic_arn:
            logger.info(f"알림 비활성화됨: {subject}")
            return

        try:
            # 메시지 포맷팅
            formatted_message = self._format_message(subject, message, data)

            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Subject=f"🤖 비트코인 봇: {subject}",
                Message=formatted_message,
            )

            logger.info(f"알림 발송 성공: {response['MessageId']}")
            return response["MessageId"]

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"SNS 알림 발송 실패 ({error_code}): {e}")
            return None
        except Exception as e:
            logger.error(f"알림 발송 중 예외 발생: {e}")
            return None

    def _format_message(
        self, subject: str, message: str, data: Optional[Dict] = None
    ) -> str:
        """메시지 포맷팅"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted = f"""
⏰ 시간: {timestamp}
📢 제목: {subject}
💬 내용: {message}
"""

        if data:
            formatted += "\n📊 상세 정보:\n"
            for key, value in data.items():
                if key == "price":
                    formatted += f"  💰 {key}: ${value:,.2f}\n"
                elif key == "profit":
                    formatted += f"  💵 {key}: ${value:.2f}\n"
                elif key == "profit_rate":
                    formatted += f"  📈 수익률: {value*100:.2f}%\n"
                elif key == "balance":
                    formatted += f"  💳 잔고: ${value:.2f}\n"
                elif key == "amount":
                    formatted += f"  ⚖️ 수량: {value:.6f} BTC\n"
                else:
                    formatted += f"  📄 {key}: {value}\n"

        return formatted.strip()

    def notify_trade_executed(
        self, action: str, price: float, amount: float, balance: float
    ):
        """거래 실행 알림"""
        if action == "BUY":
            subject = "💰 매수 주문 실행"
            message = "BTC를 매수했습니다!"
        else:
            subject = "💸 매도 주문 실행"
            message = "BTC를 매도했습니다!"

        data = {
            "action": action,
            "price": price,
            "amount": amount,
            "balance": balance,
        }

        self.send_notification(subject, message, data)

    def notify_profit_achieved(
        self, buy_price: float, sell_price: float, profit: float, profit_rate: float
    ):
        """수익 달성 알림"""
        subject = "🎉 수익 실현!"
        message = "거래에서 수익을 실현했습니다!"

        data = {
            "buy_price": buy_price,
            "sell_price": sell_price,
            "profit": profit,
            "profit_rate": profit_rate,
        }

        self.send_notification(subject, message, data)

    def notify_insufficient_balance(self, required: float, available: float):
        """잔고 부족 알림"""
        subject = "⚠️ 잔고 부족"
        message = "매수에 필요한 자금이 부족합니다."

        data = {
            "required": required,
            "available": available,
            "shortage": required - available,
        }

        self.send_notification(subject, message, data)

    def notify_error(
        self, error_type: str, error_message: str, details: Optional[Dict] = None
    ):
        """에러 발생 알림"""
        subject = f"❌ 오류 발생: {error_type}"
        message = f"거래 봇에서 오류가 발생했습니다: {error_message}"

        self.send_notification(subject, message, details)

    def notify_bot_started(self):
        """봇 시작 알림"""
        subject = "🚀 거래 봇 시작"
        message = "비트코인 자동거래 봇이 시작되었습니다."

        trading_config = config_loader.get_trading_config()
        data = {
            "symbol": trading_config.get("symbol"),
            "sma_short": trading_config.get("sma_short"),
            "sma_long": trading_config.get("sma_long"),
            "trade_amount": trading_config.get("trade_amount"),
        }

        self.send_notification(subject, message, data)

    def notify_no_action(self, reason: str):
        """거래 없음 알림 (선택적)"""
        # 너무 빈번한 알림을 피하기 위해 로그만 남김
        logger.info(f"거래 없음: {reason}")


# 전역 알림 인스턴스
notifier = TradingNotifier()
