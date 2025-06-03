#!/usr/bin/env python3
"""
Bitcoin Auto Trading Backtest

사용법:
python backtest.py --start 2024-05-01 --end 2024-05-30
python backtest.py --start 2024-05-01 --end 2024-05-30 --plot
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta

import ccxt
import pandas as pd

from config_loader import config_loader

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self):
        # 설정 파일에서 거래 설정 로드
        trading_config = config_loader.get_trading_config()
        exchange_config = config_loader.get_exchange_config()
        
        self.symbol = trading_config.get("symbol", "BTC/USDT")
        self.timeframe = trading_config.get("timeframe", "5m")
        self.sma_short = trading_config.get("sma_short", 7)
        self.sma_long = trading_config.get("sma_long", 25)
        self.initial_balance = trading_config.get("initial_balance", 100.0)
        self.trade_amount = trading_config.get("trade_amount", 90.0)
        self.trading_fee = trading_config.get("trading_fee", 0.001)
        self.profit_threshold = trading_config.get("profit_threshold", 0.003)

        # 바이낸스 거래소 (데이터 조회용)
        self.exchange = ccxt.binance(
            {
                "enableRateLimit": exchange_config.get("enable_rate_limit", True),
            }
        )

    def fetch_historical_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """과거 데이터 조회"""
        try:
            start_timestamp = int(
                datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000
            )
            end_timestamp = int(
                datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000
            )

            all_ohlcv = []
            current_timestamp = start_timestamp

            logger.info(f"Fetching historical data from {start_date} to {end_date}")

            while current_timestamp < end_timestamp:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    since=current_timestamp,
                    limit=1000,
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)
                current_timestamp = ohlcv[-1][0] + 300000  # 5분 추가

                # API 레이트 리미트 고려
                import time

                time.sleep(0.1)

            # DataFrame 생성
            df = pd.DataFrame(
                all_ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            # 중복 제거 및 정렬
            df = df[~df.index.duplicated(keep="first")]
            df = df.sort_index()

            # 지정된 기간으로 필터링
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date) + timedelta(days=1)
            df = df[(df.index >= start_dt) & (df.index < end_dt)]

            logger.info(f"Fetched {len(df)} data points")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            raise

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()
        df[f"sma_{self.sma_short}"] = df["close"].rolling(window=self.sma_short).mean()
        df[f"sma_{self.sma_long}"] = df["close"].rolling(window=self.sma_long).mean()

        # 매수/매도 신호 계산
        df["buy_signal"] = (
            df[f"sma_{self.sma_short}"] > df[f"sma_{self.sma_long}"]
        ) & (
            df[f"sma_{self.sma_short}"].shift(1) <= df[f"sma_{self.sma_long}"].shift(1)
        )

        return df

    def run_backtest(self, df: pd.DataFrame) -> dict:
        """백테스트 실행"""
        results = {"trades": [], "balance_history": [], "position_history": []}

        balance = self.initial_balance
        position = None  # {'price': float, 'amount': float, 'timestamp': datetime}

        for i, (timestamp, row) in enumerate(df.iterrows()):
            current_price = row["close"]
            sma_short = row[f"sma_{self.sma_short}"]
            sma_long = row[f"sma_{self.sma_long}"]

            # 지표가 계산되지 않은 초기 구간 스킵
            if pd.isna(sma_short) or pd.isna(sma_long):
                results["balance_history"].append(
                    {
                        "timestamp": timestamp,
                        "balance": balance,
                        "position_value": 0,
                        "total_value": balance,
                    }
                )
                results["position_history"].append(
                    {"timestamp": timestamp, "position": None}
                )
                continue

            # 매수 조건 확인
            if (
                position is None
                and sma_short > sma_long
                and balance >= self.trade_amount
            ):
                # 매수 실행
                btc_amount = (
                    self.trade_amount * (1 - self.trading_fee)
                ) / current_price
                position = {
                    "price": current_price,
                    "amount": btc_amount,
                    "timestamp": timestamp,
                }
                balance -= self.trade_amount

                results["trades"].append(
                    {
                        "type": "BUY",
                        "timestamp": timestamp,
                        "price": current_price,
                        "amount": btc_amount,
                        "cost": self.trade_amount,
                        "balance_after": balance,
                    }
                )

                logger.info(
                    f"BUY at {timestamp}: ${current_price:.2f}, Amount: {btc_amount:.6f} BTC"
                )

            # 매도 조건 확인
            elif position is not None:
                # 수익률 계산 (실제 매도시 받을 금액 기준)
                gross_profit_rate = (current_price - position["price"]) / position["price"]
                # 실제 수익률 = 총 수익률 - 매수/매도 수수료
                profit_rate = gross_profit_rate - (2 * self.trading_fee)

                if sma_short < sma_long and profit_rate >= self.profit_threshold:
                    # 매도 실행
                    sell_value = (
                        position["amount"] * current_price * (1 - self.trading_fee)
                    )
                    balance += sell_value

                    trade_profit = sell_value - self.trade_amount

                    results["trades"].append(
                        {
                            "type": "SELL",
                            "timestamp": timestamp,
                            "price": current_price,
                            "amount": position["amount"],
                            "revenue": sell_value,
                            "profit": trade_profit,
                            "profit_rate": profit_rate,
                            "balance_after": balance,
                            "hold_days": (
                                timestamp - position["timestamp"]
                            ).total_seconds()
                            / (24 * 3600),
                        }
                    )

                    logger.info(
                        f"SELL at {timestamp}: ${current_price:.2f}, Profit: ${trade_profit:.2f} ({profit_rate*100:.2f}%)"
                    )
                    position = None

            # 현재 상태 기록
            position_value = position["amount"] * current_price if position else 0
            total_value = balance + position_value

            results["balance_history"].append(
                {
                    "timestamp": timestamp,
                    "balance": balance,
                    "position_value": position_value,
                    "total_value": total_value,
                }
            )

            results["position_history"].append(
                {
                    "timestamp": timestamp,
                    "position": position.copy() if position else None,
                }
            )

        return results

    def calculate_performance_metrics(self, results: dict, df: pd.DataFrame) -> dict:
        """성과 지표 계산"""
        balance_history = pd.DataFrame(results["balance_history"])
        trades = results["trades"]

        # 기본 지표
        initial_value = self.initial_balance
        final_value = balance_history["total_value"].iloc[-1]
        total_return = (final_value - initial_value) / initial_value

        # 거래 관련 지표
        sell_trades = [t for t in trades if t["type"] == "SELL"]

        total_trades = len(sell_trades)
        winning_trades = len([t for t in sell_trades if t["profit"] > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_profit = sum([t["profit"] for t in sell_trades])
        avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0

        # Buy & Hold 대비 성과
        buy_hold_return = (df["close"].iloc[-1] - df["close"].iloc[0]) / df[
            "close"
        ].iloc[0]

        # 최대 손실 (MDD)
        balance_history["peak"] = balance_history["total_value"].cummax()
        balance_history["drawdown"] = (
            balance_history["total_value"] - balance_history["peak"]
        ) / balance_history["peak"]
        max_drawdown = balance_history["drawdown"].min()

        return {
            "initial_value": initial_value,
            "final_value": final_value,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "buy_hold_return": buy_hold_return,
            "buy_hold_return_pct": buy_hold_return * 100,
            "outperformance": total_return - buy_hold_return,
            "outperformance_pct": (total_return - buy_hold_return) * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate": win_rate,
            "win_rate_pct": win_rate * 100,
            "total_profit": total_profit,
            "avg_profit_per_trade": avg_profit_per_trade,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown * 100,
        }

    def print_results(self, results: dict, metrics: dict):
        """결과 출력"""
        print("\n" + "=" * 60)
        print("백테스트 결과")
        print("=" * 60)

        print(f"초기 자산: ${metrics['initial_value']:.2f}")
        print(f"최종 자산: ${metrics['final_value']:.2f}")
        print(f"총 수익률: {metrics['total_return_pct']:.2f}%")
        print(f"Buy & Hold 수익률: {metrics['buy_hold_return_pct']:.2f}%")
        print(f"전략 초과 수익률: {metrics['outperformance_pct']:.2f}%")
        print()

        print(f"총 거래 횟수: {metrics['total_trades']}")
        print(
            f"승률: {metrics['win_rate_pct']:.1f}% ({metrics['winning_trades']}/{metrics['total_trades']})"
        )
        print(f"총 수익: ${metrics['total_profit']:.2f}")
        print(f"거래당 평균 수익: ${metrics['avg_profit_per_trade']:.2f}")
        print(f"최대 손실: {metrics['max_drawdown_pct']:.2f}%")
        print()

        # 거래 내역
        if results["trades"]:
            print("거래 내역:")
            print("-" * 80)
            print(
                f"{'Type':<4} {'Date':<19} {'Price':<10} {'Amount':<12} {'Profit':<10} {'Rate':<8}"
            )
            print("-" * 80)

            for trade in results["trades"]:
                if trade["type"] == "SELL":
                    print(
                        f"{trade['type']:<4} {trade['timestamp'].strftime('%Y-%m-%d %H:%M'):<19} "
                        f"${trade['price']:<9.2f} {trade['amount']:<12.6f} "
                        f"${trade['profit']:<9.2f} {trade['profit_rate']*100:<7.2f}%"
                    )
                else:
                    print(
                        f"{trade['type']:<4} {trade['timestamp'].strftime('%Y-%m-%d %H:%M'):<19} "
                        f"${trade['price']:<9.2f} {trade['amount']:<12.6f} {'':>10} {'':>8}"
                    )

    def plot_results(self, df: pd.DataFrame, results: dict):
        """결과 시각화"""
        try:
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt

            # 설정에서 차트 크기 가져오기
            backtest_config = config_loader.get_backtest_config()
            chart_size = backtest_config.get("chart_size", [15, 12])
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=chart_size)

            # 1. 가격 차트와 SMA
            ax1.plot(
                df.index, df["close"], label="BTC Price", color="black", linewidth=1
            )
            ax1.plot(
                df.index,
                df[f"sma_{self.sma_short}"],
                label=f"SMA({self.sma_short})",
                color="blue",
            )
            ax1.plot(
                df.index,
                df[f"sma_{self.sma_long}"],
                label=f"SMA({self.sma_long})",
                color="red",
            )

            # 매수/매도 포인트 표시
            buy_trades = [t for t in results["trades"] if t["type"] == "BUY"]
            sell_trades = [t for t in results["trades"] if t["type"] == "SELL"]

            if buy_trades:
                buy_dates = [t["timestamp"] for t in buy_trades]
                buy_prices = [t["price"] for t in buy_trades]
                ax1.scatter(
                    buy_dates,
                    buy_prices,
                    color="green",
                    marker="^",
                    s=100,
                    label="Buy",
                    zorder=5,
                )

            if sell_trades:
                sell_dates = [t["timestamp"] for t in sell_trades]
                sell_prices = [t["price"] for t in sell_trades]
                ax1.scatter(
                    sell_dates,
                    sell_prices,
                    color="red",
                    marker="v",
                    s=100,
                    label="Sell",
                    zorder=5,
                )

            ax1.set_title("BTC Price and Trading Signals")
            ax1.set_ylabel("Price (USDT)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. 포트폴리오 가치
            balance_df = pd.DataFrame(results["balance_history"])
            ax2.plot(
                balance_df["timestamp"],
                balance_df["total_value"],
                label="Portfolio Value",
                color="green",
                linewidth=2,
            )
            ax2.axhline(
                y=self.initial_balance,
                color="gray",
                linestyle="--",
                alpha=0.7,
                label="Initial Value",
            )

            ax2.set_title("Portfolio Value Over Time")
            ax2.set_ylabel("Value (USDT)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 3. 수익률 비교
            balance_df["strategy_return"] = (
                balance_df["total_value"] / self.initial_balance - 1
            ) * 100
            buy_hold_return = (df["close"] / df["close"].iloc[0] - 1) * 100

            ax3.plot(
                balance_df["timestamp"],
                balance_df["strategy_return"],
                label="Strategy Return",
                color="blue",
                linewidth=2,
            )
            ax3.plot(
                df.index,
                buy_hold_return,
                label="Buy & Hold Return",
                color="orange",
                linewidth=2,
            )
            ax3.axhline(y=0, color="gray", linestyle="-", alpha=0.3)

            ax3.set_title("Return Comparison")
            ax3.set_ylabel("Return (%)")
            ax3.set_xlabel("Date")
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 날짜 포맷 설정
            for ax in [ax1, ax2, ax3]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()
            plt.show()

        except ImportError:
            print("\n⚠️  matplotlib이 설치되지 않아 차트를 표시할 수 없습니다.")
            print("차트를 보려면 다음 명령어로 설치하세요: pip install matplotlib")


def main():
    parser = argparse.ArgumentParser(description="Bitcoin Auto Trading Backtest")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--plot", action="store_true", help="Show plot")

    args = parser.parse_args()

    try:
        # 백테스트 엔진 초기화
        engine = BacktestEngine()

        # 과거 데이터 조회
        df = engine.fetch_historical_data(args.start, args.end)

        if len(df) == 0:
            print("⚠️  데이터를 찾을 수 없습니다. 날짜 범위를 확인해주세요.")
            sys.exit(1)

        # 기술적 지표 계산
        df = engine.calculate_indicators(df)

        # 백테스트 실행
        results = engine.run_backtest(df)

        # 성과 지표 계산
        metrics = engine.calculate_performance_metrics(results, df)

        # 결과 출력
        engine.print_results(results, metrics)

        # 차트 출력
        if args.plot:
            engine.plot_results(df, results)

    except KeyboardInterrupt:
        print("\n백테스트가 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
