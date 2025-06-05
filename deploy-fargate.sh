#!/bin/bash
set -e

echo "🚀 Deploying Bitcoin Trading Bot to AWS Fargate..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 환경 변수 확인
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET" ]; then
    echo -e "${RED}❌ 환경 변수가 설정되지 않았습니다.${NC}"
    echo "다음 환경 변수를 설정해주세요:"
    echo "  export BINANCE_API_KEY='your_api_key'"
    echo "  export BINANCE_SECRET='your_secret_key'"
    exit 1
fi

# AWS 계정 및 리전 설정
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-ap-northeast-2}

echo -e "${BLUE}📋 배포 정보${NC}"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  AWS Region: $AWS_REGION"
echo ""

# 1. AWS Secrets Manager에 바이낸스 API 키 저장
echo -e "${YELLOW}🔐 Storing Binance API credentials in Secrets Manager...${NC}"
aws secretsmanager create-secret \
    --name "bitcoin-trading/binance" \
    --description "Binance API credentials for Bitcoin trading bot" \
    --secret-string "{\"api_key\":\"$BINANCE_API_KEY\",\"secret\":\"$BINANCE_SECRET\"}" \
    --region $AWS_REGION 2>/dev/null || \
aws secretsmanager update-secret \
    --secret-id "bitcoin-trading/binance" \
    --secret-string "{\"api_key\":\"$BINANCE_API_KEY\",\"secret\":\"$BINANCE_SECRET\"}" \
    --region $AWS_REGION

echo -e "${GREEN}✅ Secrets stored successfully${NC}"

# 2. CDK Bootstrap (처음 한 번만 필요)
echo -e "${YELLOW}🔧 CDK Bootstrap (if needed)...${NC}"
cd cdk
pip install -r requirements.txt
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION 2>/dev/null || echo "Bootstrap already done"

# 3. CDK Deploy
echo -e "${YELLOW}☁️ Deploying infrastructure with CDK...${NC}"
cdk deploy --require-approval never

# CDK 출력 값들 가져오기
ECR_REPO_URI=$(aws cloudformation describe-stacks \
    --stack-name BitcoinTradingStack \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryURI`].OutputValue' \
    --output text)

echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
echo "  ECR Repository: $ECR_REPO_URI"

# 4. Docker 이미지 빌드 및 푸시
echo -e "${YELLOW}🐳 Building and pushing Docker image...${NC}"
cd ..

# ECR 로그인
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URI

# Docker 이미지 빌드
docker build -t bitcoin-auto-trader .

# 태그 설정 및 푸시
docker tag bitcoin-auto-trader:latest $ECR_REPO_URI:latest
docker push $ECR_REPO_URI:latest

echo -e "${GREEN}✅ Docker image pushed successfully${NC}"

# 5. 첫 번째 태스크 수동 실행 (테스트)
echo -e "${YELLOW}🧪 Running initial test task...${NC}"
CLUSTER_NAME="bitcoin-trading-cluster"
TASK_DEF_ARN=$(aws ecs list-task-definitions \
    --family-prefix bitcoin-trading-task \
    --query 'taskDefinitionArns[0]' \
    --output text)

# 기본 VPC의 첫 번째 공용 서브넷 가져오기
SUBNET_ID=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)" \
    --filters "Name=map-public-ip-on-launch,Values=true" \
    --query 'Subnets[0].SubnetId' \
    --output text)

# 태스크 실행
TASK_ARN=$(aws ecs run-task \
    --cluster $CLUSTER_NAME \
    --task-definition $TASK_DEF_ARN \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],assignPublicIp=ENABLED}" \
    --query 'tasks[0].taskArn' \
    --output text)

echo -e "${GREEN}✅ Test task started: $TASK_ARN${NC}"

# 6. SNS 토픽 정보 출력
SNS_TOPIC_ARN=$(aws cloudformation describe-stacks \
    --stack-name BitcoinTradingStack \
    --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' \
    --output text)

echo ""
echo -e "${GREEN}🎉 배포가 완료되었습니다!${NC}"
echo ""
echo -e "${BLUE}📞 알림 설정:${NC}"
echo "  다음 명령어로 이메일 알림을 설정하세요:"
echo "  aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com"
echo ""
echo -e "${BLUE}📊 모니터링:${NC}"
echo "  CloudWatch Logs: /aws/ecs/bitcoin-trading"
echo "  ECS 클러스터: $CLUSTER_NAME"
echo ""
echo -e "${BLUE}⏰ 스케줄:${NC}"
echo "  거래 봇이 10분마다 자동 실행됩니다"
echo ""
echo -e "${YELLOW}⚠️ 주의사항:${NC}"
echo "  - 바이낸스 계정에 충분한 USDT를 입금해주세요"
echo "  - 첫 번째 실행 로그를 확인하여 정상 작동을 확인하세요"
echo "  - 필요시 config.json에서 거래 설정을 조정하세요" 