#!/usr/bin/env python3
import json
import os
from datetime import datetime
from state_store import StateStore

# .env 파일 수동 로드
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# State Store 초기화
use_s3 = os.getenv("USE_S3", "true").lower() == "true"
state_store = StateStore(use_s3=use_s3)

print("🔍 현재 상태 확인...")
current_state = state_store.load_state()
print(f"현재 상태: {json.dumps(current_state, indent=2, ensure_ascii=False)}")

# 올바른 포지션 정보로 복구
print("\n🔧 포지션 정보 복구 중...")
corrected_state = {
    "trading_pair": "BTC/USDT",
    "position": {
        "buy_price": 108225.15,
        "buy_amount": 0.00045954,  # 실제 보유량
        "buy_time": "2025-06-12T17:27:21.236000",
        "order_id": "44590407978"  # 로그에서 확인된 주문 ID
    },
    "last_trade": None,
    "total_trades": 0,
    "total_profit": 0.0,
    "created_at": current_state.get("created_at", datetime.now().isoformat()),
    "updated_at": datetime.now().isoformat()
}

print(f"복구할 상태: {json.dumps(corrected_state, indent=2, ensure_ascii=False)}")

# 상태 저장
state_store.save_state(corrected_state)
print("\n✅ 상태가 성공적으로 복구되었습니다!")

# 복구 확인
print("\n🔍 복구 후 상태 확인...")
restored_state = state_store.load_state()
print(f"복구된 상태: {json.dumps(restored_state, indent=2, ensure_ascii=False)}") 