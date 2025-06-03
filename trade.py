import logging
import os
from datetime import datetime
from typing import Any, Dict

import ccxt
import pandas as pd
from botocore.exceptions import ClientError

from config_loader import config_loader
from notification import notifier

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self):
        """바이낸스 거래 봇 초기화"""
        # 설정 파일에서 거래 설정 로드
        trading_config = config_loader.get_trading_config()
        exchange_config = config_loader.get_exchange_config()
        
        self.symbol = trading_config.get("symbol", "BTC/USDT")
        self.timeframe = trading_config.get("timeframe", "5m")
        self.sma_short = trading_config.get("sma_short", 7)
        self.sma_long = trading_config.get("sma_long", 25)
        self.trade_amount = trading_config.get("trade_amount", 90.0)
        self.profit_threshold = trading_config.get("profit_threshold", 0.003)
        self.trading_fee = trading_config.get("trading_fee", 0.001)

        # 바이낸스 거래소 초기화
        self.exchange = ccxt.binance(
            {
                "apiKey": os.getenv("BINANCE_API_KEY"),
                "secret": os.getenv("BINANCE_SECRET"),
                "sandbox": exchange_config.get("sandbox", False),
                "enableRateLimit": exchange_config.get("enable_rate_limit", True),
            }
        )

    def get_ohlcv_data(self, limit: int = 100) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.symbol, timeframe=self.timeframe, limit=limit
            )

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            return df
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            raise

    def calculate_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """단순 이동평균 계산"""
        df[f"sma_{self.sma_short}"] = df["close"].rolling(window=self.sma_short).mean()
        df[f"sma_{self.sma_long}"] = df["close"].rolling(window=self.sma_long).mean()
        return df

    def get_current_balance(self) -> Dict[str, float]:
        """현재 잔고 조회"""
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance["USDT"]["free"]
            btc_balance = balance["BTC"]["free"]
            
            logger.info(f"현재 잔고 - USDT: ${usdt_balance:.2f}, BTC: {btc_balance:.6f}")
            return {"USDT": usdt_balance, "BTC": btc_balance}
            
        except ccxt.NetworkError as e:
            error_msg = f"네트워크 오류로 잔고 조회 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("네트워크 오류", error_msg)
            raise
        except ccxt.ExchangeError as e:
            error_msg = f"거래소 오류로 잔고 조회 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("거래소 오류", error_msg)
            raise
        except Exception as e:
            error_msg = f"예상치 못한 오류로 잔고 조회 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("잔고 조회 실패", error_msg)
            raise

    def place_buy_order(self, amount_usdt: float) -> Dict[str, Any]:
        """매수 주문"""
        try:
            # 현재 가격 조회
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker["last"]

            # BTC 수량 계산 (수수료 고려)
            btc_amount = (amount_usdt * (1 - self.trading_fee)) / current_price

            logger.info(f"매수 주문 시도 - 가격: ${current_price:.2f}, 수량: {btc_amount:.6f} BTC")

            # 시장가 매수 주문
            order = self.exchange.create_market_buy_order(
                symbol=self.symbol, amount=btc_amount
            )

            logger.info(f"매수 주문 성공: {order['id']}")
            
            # 거래 실행 알림
            notifier.notify_trade_executed("BUY", current_price, btc_amount, 0)  # 잔고는 나중에 업데이트
            
            return {
                "order_id": order["id"],
                "amount": btc_amount,
                "price": current_price,
                "cost": amount_usdt,
                "timestamp": datetime.now(),
            }
            
        except ccxt.InsufficientFunds as e:
            error_msg = f"잔고 부족으로 매수 주문 실패 - 필요: ${amount_usdt:.2f}"
            logger.error(error_msg)
            notifier.notify_error("잔고 부족", error_msg, {"required_amount": amount_usdt})
            raise
        except ccxt.NetworkError as e:
            error_msg = f"네트워크 오류로 매수 주문 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("네트워크 오류", error_msg)
            raise
        except ccxt.ExchangeError as e:
            error_msg = f"거래소 오류로 매수 주문 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("거래소 오류", error_msg)
            raise
        except Exception as e:
            error_msg = f"예상치 못한 오류로 매수 주문 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("매수 주문 실패", error_msg)
            raise

    def place_sell_order(self, btc_amount: float) -> Dict[str, Any]:
        """매도 주문"""
        try:
            logger.info(f"매도 주문 시도 - 수량: {btc_amount:.6f} BTC")
            
            # 시장가 매도 주문
            order = self.exchange.create_market_sell_order(
                symbol=self.symbol, amount=btc_amount
            )

            sell_price = order["price"] or order["average"]
            sell_cost = order["cost"]
            
            logger.info(f"매도 주문 성공: {order['id']} - 가격: ${sell_price:.2f}")
            
            # 거래 실행 알림
            notifier.notify_trade_executed("SELL", sell_price, btc_amount, 0)  # 잔고는 나중에 업데이트
            
            return {
                "order_id": order["id"],
                "amount": btc_amount,
                "price": sell_price,
                "cost": sell_cost,
                "timestamp": datetime.now(),
            }
            
        except ccxt.InsufficientFunds as e:
            error_msg = f"보유 BTC 부족으로 매도 주문 실패 - 필요: {btc_amount:.6f} BTC"
            logger.error(error_msg)
            notifier.notify_error("보유량 부족", error_msg, {"required_btc": btc_amount})
            raise
        except ccxt.NetworkError as e:
            error_msg = f"네트워크 오류로 매도 주문 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("네트워크 오류", error_msg)
            raise
        except ccxt.ExchangeError as e:
            error_msg = f"거래소 오류로 매도 주문 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("거래소 오류", error_msg)
            raise
        except Exception as e:
            error_msg = f"예상치 못한 오류로 매도 주문 실패: {e}"
            logger.error(error_msg)
            notifier.notify_error("매도 주문 실패", error_msg)
            raise

    def should_buy(self, df: pd.DataFrame, current_state: Dict[str, Any]) -> bool:
        """매수 조건 확인"""
        if current_state.get("position") is not None:
            return False  # 이미 포지션 보유 중

        latest = df.iloc[-1]
        sma_short = latest[f"sma_{self.sma_short}"]
        sma_long = latest[f"sma_{self.sma_long}"]

        # SMA(7) > SMA(25) 매수 신호
        return sma_short > sma_long and not pd.isna(sma_short) and not pd.isna(sma_long)

    def should_sell(self, df: pd.DataFrame, current_state: Dict[str, Any]) -> bool:
        """매도 조건 확인"""
        position = current_state.get("position")
        if position is None:
            return False  # 보유 포지션 없음

        latest = df.iloc[-1]
        current_price = latest["close"]
        buy_price = position["buy_price"]

        sma_short = latest[f"sma_{self.sma_short}"]
        sma_long = latest[f"sma_{self.sma_long}"]

        # 수익률 계산 (실제 매도시 받을 금액 기준)
        gross_profit_rate = (current_price - buy_price) / buy_price
        # 실제 수익률 = 총 수익률 - 매수/매도 수수료
        profit_rate = gross_profit_rate - (2 * self.trading_fee)

        # SMA(7) < SMA(25) and 수익률 >= 0.3%
        sma_condition = (
            sma_short < sma_long and not pd.isna(sma_short) and not pd.isna(sma_long)
        )
        profit_condition = profit_rate >= self.profit_threshold

        return sma_condition and profit_condition

    def execute_strategy(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """전략 실행"""
        try:
            # OHLCV 데이터 조회 및 SMA 계산
            df = self.get_ohlcv_data()
            df = self.calculate_sma(df)

            # 현재 잔고 조회
            balance = self.get_current_balance()

            result = {
                "action": "NO_ACTION",
                "message": "No trading signal",
                "current_balance": balance,
                "current_position": current_state.get("position"),
                "state_changed": False,
            }

            # 매수 조건 확인
            if self.should_buy(df, current_state):
                if balance["USDT"] >= self.trade_amount:
                    order_result = self.place_buy_order(self.trade_amount)

                    new_state = current_state.copy()
                    new_state["position"] = {
                        "buy_price": order_result["price"],
                        "buy_amount": order_result["amount"],
                        "buy_time": order_result["timestamp"].isoformat(),
                        "order_id": order_result["order_id"],
                    }

                    result.update(
                        {
                            "action": "BUY",
                            "message": f"매수 주문 실행 완료 - 가격: ${order_result['price']:.2f}",
                            "new_state": new_state,
                            "state_changed": True,
                        }
                    )
                else:
                    # 잔고 부족 알림
                    shortage = self.trade_amount - balance["USDT"]
                    result["message"] = f"USDT 잔고 부족: 보유 ${balance['USDT']:.2f}, 필요 ${self.trade_amount:.2f} (부족: ${shortage:.2f})"
                    notifier.notify_insufficient_balance(self.trade_amount, balance["USDT"])

            # 매도 조건 확인
            elif self.should_sell(df, current_state):
                position = current_state["position"]
                order_result = self.place_sell_order(position["buy_amount"])

                # 수익 계산
                profit = order_result["cost"] - self.trade_amount
                profit_rate = (order_result["price"] - position["buy_price"]) / position["buy_price"]

                new_state = current_state.copy()
                new_state["position"] = None
                new_state["last_trade"] = {
                    "buy_price": position["buy_price"],
                    "sell_price": order_result["price"],
                    "profit": profit,
                    "profit_rate": profit_rate,
                    "sell_time": order_result["timestamp"].isoformat(),
                }

                # 수익 실현 알림
                notifier.notify_profit_achieved(
                    position["buy_price"], 
                    order_result["price"], 
                    profit, 
                    profit_rate
                )

                result.update(
                    {
                        "action": "SELL",
                        "message": f"매도 주문 실행 완료 - 가격: ${order_result['price']:.2f}, 수익: ${profit:.2f} ({profit_rate*100:.2f}%)",
                        "new_state": new_state,
                        "state_changed": True,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            raise
