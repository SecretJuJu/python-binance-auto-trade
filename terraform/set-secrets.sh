#!/bin/bash

# Binance API Credentials 설정 스크립트
# 사용법: ./set-secrets.sh

set -e

echo "🔐 Binance API 자격증명을 Secrets Manager에 설정합니다..."

# API 키 입력 받기
read -p "Binance API Key를 입력하세요: " BINANCE_API_KEY
read -s -p "Binance Secret Key를 입력하세요: " BINANCE_SECRET_KEY
echo

# 입력값 검증
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET_KEY" ]; then
    echo "❌ API 키와 Secret 키를 모두 입력해야 합니다."
    exit 1
fi

# Get the secret ARN from Terraform output
SECRET_ARN=$(terraform output -raw secrets_manager_secret_arn)

# Secret JSON 생성
SECRET_JSON=$(cat <<EOF
{
  "api_key": "$BINANCE_API_KEY",
  "secret_key": "$BINANCE_SECRET_KEY"
}
EOF
)

# Secrets Manager에 저장
echo "📝 Secrets Manager에 자격증명을 저장합니다..."
aws secretsmanager put-secret-value \
    --secret-id "$SECRET_ARN" \
    --secret-string "$SECRET_JSON"

if [ $? -eq 0 ]; then
    echo "✅ Binance API 자격증명이 성공적으로 저장되었습니다!"
    echo "🚀 이제 ECS 태스크를 다시 실행해보세요."
else
    echo "❌ 자격증명 저장에 실패했습니다."
    exit 1
fi

# 설정 확인
echo ""
echo "🔍 설정 확인..."
echo "Secret ARN: $SECRET_ARN"
echo ""
echo "📋 다음 명령어로 ECS 태스크를 수동 실행할 수 있습니다:"
echo ""
echo "aws ecs run-task \\"
echo "    --cluster bitcoin-auto-trader-cluster \\"
echo "    --task-definition bitcoin-auto-trader-task \\"
echo "    --launch-type FARGATE \\"
echo "    --network-configuration 'awsvpcConfiguration={subnets=[subnet-XXXXXXXX],securityGroups=[sg-XXXXXXXX],assignPublicIp=ENABLED}'"
echo ""
echo "💡 실제 subnet과 security group ID는 Terraform output에서 확인하세요." 