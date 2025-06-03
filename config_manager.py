#!/usr/bin/env python3
"""
설정 관리 CLI 도구

사용법:
python config_manager.py show                    # 현재 설정 보기
python config_manager.py set trade_amount 50     # 거래 금액 변경
python config_manager.py set sma_short 5         # 단기 SMA 변경
python config_manager.py preset conservative     # 보수적 설정 적용
python config_manager.py preset aggressive       # 공격적 설정 적용
"""

import argparse
import json
import sys

from config_loader import config_loader


class ConfigManager:
    """설정 관리 클래스"""

    PRESETS = {
        "conservative": {
            "trading": {
                "sma_short": 10,
                "sma_long": 30,
                "trade_amount": 20.0,
                "profit_threshold": 0.005,  # 0.5%
            }
        },
        "balanced": {
            "trading": {
                "sma_short": 7,
                "sma_long": 25,
                "trade_amount": 50.0,
                "profit_threshold": 0.003,  # 0.3%
            }
        },
        "aggressive": {
            "trading": {
                "sma_short": 5,
                "sma_long": 15,
                "trade_amount": 90.0,
                "profit_threshold": 0.002,  # 0.2%
            }
        },
    }

    def show_config(self):
        """현재 설정 출력"""
        config = config_loader.load_config()
        print("=" * 60)
        print("현재 설정")
        print("=" * 60)
        print(json.dumps(config, indent=2, ensure_ascii=False))

    def show_trading_config(self):
        """거래 설정만 출력"""
        trading_config = config_loader.get_trading_config()
        print("=" * 40)
        print("거래 설정")
        print("=" * 40)
        for key, value in trading_config.items():
            if key == "profit_threshold":
                print(f"{key}: {value} ({value*100:.1f}%)")
            else:
                print(f"{key}: {value}")

    def set_value(self, key: str, value: str):
        """설정 값 변경"""
        try:
            # 숫자 변환 시도
            if "." in value:
                converted_value = float(value)
            else:
                try:
                    converted_value = int(value)
                except ValueError:
                    converted_value = value
        except ValueError:
            converted_value = value

        # 불린 값 처리
        if value.lower() in ["true", "false"]:
            converted_value = value.lower() == "true"

        config_loader.update_trading_config(**{key: converted_value})
        print(f"✅ {key} = {converted_value} 로 설정되었습니다.")

    def apply_preset(self, preset_name: str):
        """프리셋 적용"""
        if preset_name not in self.PRESETS:
            print(f"❌ 사용할 수 없는 프리셋: {preset_name}")
            print(f"사용 가능한 프리셋: {', '.join(self.PRESETS.keys())}")
            return

        preset = self.PRESETS[preset_name]
        config_loader.update_trading_config(**preset["trading"])
        print(f"✅ '{preset_name}' 프리셋이 적용되었습니다.")
        self.show_trading_config()

    def list_presets(self):
        """사용 가능한 프리셋 목록 출력"""
        print("=" * 50)
        print("사용 가능한 프리셋")
        print("=" * 50)
        for preset_name, preset_config in self.PRESETS.items():
            trading = preset_config["trading"]
            print(f"\n📋 {preset_name}:")
            print(f"  SMA: ({trading['sma_short']}, {trading['sma_long']})")
            print(f"  거래금액: {trading['trade_amount']} USDT")
            print(f"  수익률: {trading['profit_threshold']*100:.1f}%")

    def validate_config(self):
        """설정 유효성 검사"""
        try:
            trading_config = config_loader.get_trading_config()
            issues = []

            # 필수 키 확인
            required_keys = [
                "symbol",
                "timeframe",
                "sma_short",
                "sma_long",
                "trade_amount",
                "profit_threshold",
                "trading_fee",
            ]

            for key in required_keys:
                if key not in trading_config:
                    issues.append(f"누락된 설정: {key}")

            # 값 범위 검사
            if trading_config.get("sma_short", 0) >= trading_config.get("sma_long", 0):
                issues.append("sma_short는 sma_long보다 작아야 합니다")

            if trading_config.get("trade_amount", 0) <= 0:
                issues.append("trade_amount는 0보다 커야 합니다")

            if trading_config.get("profit_threshold", 0) <= 0:
                issues.append("profit_threshold는 0보다 커야 합니다")

            if issues:
                print("❌ 설정 검증 실패:")
                for issue in issues:
                    print(f"  - {issue}")
                return False
            else:
                print("✅ 설정이 유효합니다.")
                return True

        except Exception as e:
            print(f"❌ 설정 파일 오류: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="거래 설정 관리 도구")
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # show 명령어
    show_parser = subparsers.add_parser("show", help="현재 설정 보기")
    show_parser.add_argument("--trading", action="store_true", help="거래 설정만 보기")

    # set 명령어
    set_parser = subparsers.add_parser("set", help="설정 값 변경")
    set_parser.add_argument("key", help="설정 키")
    set_parser.add_argument("value", help="설정 값")

    # preset 명령어
    preset_parser = subparsers.add_parser("preset", help="프리셋 적용")
    preset_parser.add_argument("name", help="프리셋 이름")

    # presets 명령어
    subparsers.add_parser("presets", help="사용 가능한 프리셋 목록")

    # validate 명령어
    subparsers.add_parser("validate", help="설정 유효성 검사")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = ConfigManager()

    try:
        if args.command == "show":
            if args.trading:
                manager.show_trading_config()
            else:
                manager.show_config()
        elif args.command == "set":
            manager.set_value(args.key, args.value)
        elif args.command == "preset":
            manager.apply_preset(args.name)
        elif args.command == "presets":
            manager.list_presets()
        elif args.command == "validate":
            manager.validate_config()

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
