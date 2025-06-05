#!/usr/bin/env python3
"""
Bitcoin Auto Trading Bot - AWS CDK App
Fargate 기반 스케줄링 인프라 구성
"""

import aws_cdk as cdk
from bitcoin_trading_stack import BitcoinTradingStack

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "ap-northeast-2",
)

# Bitcoin Trading Stack 생성
BitcoinTradingStack(
    app,
    "BitcoinTradingStack",
    env=env,
    description="Bitcoin Auto Trading Bot using AWS Fargate",
)

app.synth()
