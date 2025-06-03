import json
import os
from typing import Any, Dict


class ConfigLoader:
    """설정 파일 로더"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._config = None

    def load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        if self._config is None:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"설정 파일을 찾을 수 없습니다: {self.config_path}"
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"설정 파일 JSON 형식 오류: {e}")

        return self._config

    def get_trading_config(self) -> Dict[str, Any]:
        """거래 관련 설정 반환"""
        config = self.load_config()
        return config.get("trading", {})

    def get_exchange_config(self) -> Dict[str, Any]:
        """거래소 관련 설정 반환"""
        config = self.load_config()
        return config.get("exchange", {})

    def get_aws_config(self) -> Dict[str, Any]:
        """AWS 관련 설정 반환"""
        config = self.load_config()
        return config.get("aws", {})

    def get_backtest_config(self) -> Dict[str, Any]:
        """백테스트 관련 설정 반환"""
        config = self.load_config()
        return config.get("backtest", {})

    def update_trading_config(self, **kwargs) -> None:
        """거래 설정 업데이트 및 저장"""
        config = self.load_config()
        config["trading"].update(kwargs)
        self.save_config(config)

    def save_config(self, config: Dict[str, Any]) -> None:
        """설정 파일 저장"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self._config = config  # 캐시 업데이트


# 전역 설정 로더 인스턴스
config_loader = ConfigLoader() 