import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

import boto3

logger = logging.getLogger(__name__)


def convert_floats_to_decimal(obj):
    """DynamoDB용으로 float를 Decimal로 변환"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    return obj


def convert_decimals_to_float(obj):
    """DynamoDB에서 로드한 Decimal을 float로 변환"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(v) for v in obj]
    return obj


class StateStore:
    def __init__(self, use_s3: bool = True):
        """
        상태 저장소 초기화
        use_s3: True면 S3 사용, False면 DynamoDB 사용
        """
        self.use_s3 = use_s3
        self.trading_pair = "BTC/USDT"

        if self.use_s3:
            self.s3_client = boto3.client("s3")
            self.bucket_name = os.getenv("S3_BUCKET")
            self.object_key = (
                f'trading_state_{self.trading_pair.replace("/", "_")}.json'
            )
        else:
            self.dynamodb = boto3.resource("dynamodb")
            self.table_name = os.getenv("DYNAMODB_TABLE")
            self.table = self.dynamodb.Table(self.table_name)

    def get_default_state(self) -> Dict[str, Any]:
        """기본 상태 반환"""
        return {
            "trading_pair": self.trading_pair,
            "position": None,  # {'buy_price': float, 'buy_amount': float, 'buy_time': str}
            "last_trade": None,  # 마지막 거래 정보
            "total_trades": 0,
            "total_profit": 0.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def load_state_from_s3(self) -> Dict[str, Any]:
        """S3에서 상태 로드"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=self.object_key
            )
            state_data = json.loads(response["Body"].read().decode("utf-8"))
            logger.info("Trading state loaded from S3")
            return state_data
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("No existing state found in S3, creating default state")
            return self.get_default_state()
        except Exception as e:
            logger.error(f"Failed to load state from S3: {e}")
            return self.get_default_state()

    def save_state_to_s3(self, state: Dict[str, Any]) -> None:
        """S3에 상태 저장"""
        try:
            state["updated_at"] = datetime.now().isoformat()

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.object_key,
                Body=json.dumps(state, ensure_ascii=False, indent=2),
                ContentType="application/json",
            )
            logger.info("Trading state saved to S3")
        except Exception as e:
            logger.error(f"Failed to save state to S3: {e}")
            raise

    def load_state_from_dynamodb(self) -> Dict[str, Any]:
        """DynamoDB에서 상태 로드"""
        try:
            response = self.table.get_item(Key={"trading_pair": self.trading_pair})

            if "Item" in response:
                logger.info("Trading state loaded from DynamoDB")
                # Decimal을 float로 변환
                state_data = convert_decimals_to_float(dict(response["Item"]))
                return state_data
            else:
                logger.info(
                    "No existing state found in DynamoDB, creating default state"
                )
                return self.get_default_state()
        except Exception as e:
            logger.error(f"Failed to load state from DynamoDB: {e}")
            return self.get_default_state()

    def save_state_to_dynamodb(self, state: Dict[str, Any]) -> None:
        """DynamoDB에 상태 저장"""
        try:
            state["updated_at"] = datetime.now().isoformat()
            
            # float를 Decimal로 변환
            dynamodb_state = convert_floats_to_decimal(state)
            
            self.table.put_item(Item=dynamodb_state)
            logger.info("Trading state saved to DynamoDB")
        except Exception as e:
            logger.error(f"Failed to save state to DynamoDB: {e}")
            raise

    def load_state(self) -> Dict[str, Any]:
        """상태 로드 (S3 또는 DynamoDB)"""
        if self.use_s3:
            return self.load_state_from_s3()
        else:
            return self.load_state_from_dynamodb()

    def save_state(self, state: Dict[str, Any]) -> None:
        """상태 저장 (S3 또는 DynamoDB)"""
        if self.use_s3:
            self.save_state_to_s3(state)
        else:
            self.save_state_to_dynamodb(state)

    def get_trading_history(self, limit: int = 10) -> list:
        """거래 기록 조회 (추후 확장용)"""
        # 현재는 단순히 마지막 거래 정보만 반환
        current_state = self.load_state()
        last_trade = current_state.get("last_trade")

        if last_trade:
            return [last_trade]
        else:
            return []

    def reset_state(self) -> None:
        """상태 초기화"""
        default_state = self.get_default_state()
        self.save_state(default_state)
        logger.info("Trading state has been reset to default")


# 유틸리티 함수들
def format_state_for_display(state: Dict[str, Any]) -> str:
    """상태를 사람이 읽기 쉽게 포맷"""
    lines = []
    lines.append(f"Trading Pair: {state.get('trading_pair', 'N/A')}")
    lines.append(f"Total Trades: {state.get('total_trades', 0)}")
    lines.append(f"Total Profit: ${state.get('total_profit', 0):.2f}")

    position = state.get("position")
    if position:
        lines.append("Current Position:")
        lines.append(f"  - Buy Price: ${position.get('buy_price', 0):.2f}")
        lines.append(f"  - Amount: {position.get('buy_amount', 0):.6f} BTC")
        lines.append(f"  - Buy Time: {position.get('buy_time', 'N/A')}")
    else:
        lines.append("Current Position: None")

    last_trade = state.get("last_trade")
    if last_trade:
        lines.append("Last Trade:")
        lines.append(f"  - Buy Price: ${last_trade.get('buy_price', 0):.2f}")
        lines.append(f"  - Sell Price: ${last_trade.get('sell_price', 0):.2f}")
        lines.append(f"  - Profit: ${last_trade.get('profit', 0):.2f}")
        lines.append(f"  - Profit Rate: {last_trade.get('profit_rate', 0)*100:.2f}%")

    lines.append(f"Last Updated: {state.get('updated_at', 'N/A')}")

    return "\n".join(lines)
