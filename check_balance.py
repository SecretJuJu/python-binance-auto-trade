#!/usr/bin/env python3
import ccxt
import os

# .env 파일 수동 로드
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET'),
    'sandbox': False
})

balance = exchange.fetch_balance()
print(f'USDT: {balance["USDT"]["free"]:.6f}')
print(f'BTC: {balance["BTC"]["free"]:.8f}')

# 최근 거래 내역 확인
try:
    trades = exchange.fetch_my_trades('BTC/USDT', limit=5)
    print('\n최근 거래 내역:')
    for trade in trades:
        print(f'{trade["datetime"]} - {trade["side"]} {trade["amount"]:.8f} BTC at ${trade["price"]:.2f}')
except Exception as e:
    print(f'거래 내역 조회 실패: {e}') 