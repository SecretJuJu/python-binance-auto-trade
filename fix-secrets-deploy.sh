#!/bin/bash

# GitHub Secrets를 활용한 배포 및 시크릿 수정 스크립트
# 사용법: BINANCE_API_KEY=your_key BINANCE_SECRET=your_secret ./fix-secrets-deploy.sh

set -e

echo "🔐 Bitcoin Trading Bot 시크릿 수정 및 재배포 스크립트"
echo "=============================================="

# 환경변수 확인
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET" ]; then
    echo "❌ 필수 환경변수가 설정되지 않았습니다:"
    echo "사용법: BINANCE_API_KEY=your_key BINANCE_SECRET=your_secret ./fix-secrets-deploy.sh"
    echo ""
    echo "또는 .env 파일에 실제 값을 설정하고 실행하세요:"
    echo "source .env && ./fix-secrets-deploy.sh"
    exit 1
fi

echo "✅ 환경변수 확인 완료"

# AWS CLI 설정 확인
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI가 설치되지 않았습니다."
    echo "설치 중..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
fi

# AWS 자격증명 확인
echo "🔍 AWS 자격증명 확인 중..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS 자격증명이 설정되지 않았습니다."
    echo "다음 중 하나를 설정하세요:"
    echo "1. aws configure"
    echo "2. 환경변수: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    echo "3. IAM Role (EC2/Fargate 환경)"
    exit 1
fi

echo "✅ AWS 자격증명 확인 완료"

# 리전 설정
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-ap-northeast-2}
echo "📍 AWS 리전: $AWS_DEFAULT_REGION"

# Bitcoin Trading Bot의 Secrets Manager 시크릿 찾기
echo "🔍 기존 Secrets Manager 시크릿 검색 중..."
SECRET_NAME="bitcoin-auto-trader/binance"

# 시크릿이 존재하는지 확인
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" &> /dev/null; then
    echo "✅ 기존 시크릿 발견: $SECRET_NAME"
    
    # 시크릿 값 업데이트
    echo "🔄 Binance API 자격증명 업데이트 중..."
    SECRET_VALUE=$(cat << EOF
{
  "api_key": "$BINANCE_API_KEY",
  "secret": "$BINANCE_SECRET"
}
EOF
)
    
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_VALUE"
    
    echo "✅ 시크릿 업데이트 완료!"
    
else
    echo "❌ 시크릿을 찾을 수 없습니다: $SECRET_NAME"
    echo "🔍 다른 이름의 시크릿을 찾아보겠습니다..."
    
    # bitcoin 또는 binance가 포함된 시크릿 찾기
    SECRETS=$(aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `bitcoin`) || contains(Name, `binance`)].Name' --output text)
    
    if [ -n "$SECRETS" ]; then
        echo "📋 발견된 시크릿들:"
        echo "$SECRETS" | tr '\t' '\n' | nl
        
        # 첫 번째 시크릿 사용
        FIRST_SECRET=$(echo "$SECRETS" | cut -f1)
        echo "🎯 첫 번째 시크릿 사용: $FIRST_SECRET"
        
        SECRET_VALUE=$(cat << EOF
{
  "api_key": "$BINANCE_API_KEY",
  "secret": "$BINANCE_SECRET"
}
EOF
)
        
        aws secretsmanager put-secret-value \
            --secret-id "$FIRST_SECRET" \
            --secret-string "$SECRET_VALUE"
        
        echo "✅ 시크릿 업데이트 완료: $FIRST_SECRET"
    else
        echo "❌ Bitcoin Trading Bot 관련 시크릿을 찾을 수 없습니다."
        echo "💡 먼저 Terraform으로 인프라를 배포해야 합니다."
        exit 1
    fi
fi

# ECS 클러스터 및 태스크 정의 찾기
echo "🔍 ECS 리소스 검색 중..."
CLUSTER_NAME="bitcoin-auto-trader-cluster"
TASK_FAMILY="bitcoin-auto-trader-task"

# 클러스터 존재 확인
if aws ecs describe-clusters --clusters "$CLUSTER_NAME" --query 'clusters[0].status' --output text | grep -q "ACTIVE"; then
    echo "✅ ECS 클러스터 발견: $CLUSTER_NAME"
    
    # 최신 태스크 정의 ARN 가져오기
    TASK_DEF_ARN=$(aws ecs list-task-definitions --family-prefix "$TASK_FAMILY" --status ACTIVE --sort DESC --query 'taskDefinitionArns[0]' --output text)
    
    if [ "$TASK_DEF_ARN" != "None" ] && [ -n "$TASK_DEF_ARN" ]; then
        echo "✅ 태스크 정의 발견: $TASK_DEF_ARN"
        
        # 네트워크 설정 가져오기
        echo "🌐 네트워크 설정 준비 중..."
        
        # 기본 VPC의 퍼블릭 서브넷 가져오기
        SUBNET_ID=$(aws ec2 describe-subnets \
            --filters "Name=map-public-ip-on-launch,Values=true" \
            --query 'Subnets[0].SubnetId' \
            --output text)
        
        # 보안 그룹 ID 가져오기 (bitcoin-auto-trader 관련)
        SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=bitcoin-auto-trader-ecs-tasks" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)
        
        if [ "$SECURITY_GROUP_ID" = "None" ] || [ -z "$SECURITY_GROUP_ID" ]; then
            # 기본 보안 그룹 사용
            SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
                --filters "Name=group-name,Values=default" \
                --query 'SecurityGroups[0].GroupId' \
                --output text)
            echo "⚠️ 기본 보안 그룹 사용: $SECURITY_GROUP_ID"
        else
            echo "✅ 전용 보안 그룹 사용: $SECURITY_GROUP_ID"
        fi
        
        # 테스트 태스크 실행
        echo "🚀 테스트 태스크 실행 중..."
        TASK_ARN=$(aws ecs run-task \
            --cluster "$CLUSTER_NAME" \
            --task-definition "$TASK_DEF_ARN" \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],assignPublicIp=ENABLED,securityGroups=[$SECURITY_GROUP_ID]}" \
            --query 'tasks[0].taskArn' \
            --output text)
        
        if [ "$TASK_ARN" != "None" ] && [ -n "$TASK_ARN" ]; then
            echo "✅ 태스크 시작됨: $TASK_ARN"
            echo ""
            echo "📋 모니터링 명령어:"
            echo "  # 실시간 로그 보기"
            echo "  aws logs tail /ecs/bitcoin-auto-trader --follow"
            echo ""
            echo "  # 태스크 상태 확인"
            echo "  aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN"
            echo ""
            echo "⏰ 잠시 후 로그를 확인해보세요..."
            
            # 30초 대기 후 로그 샘플 확인
            sleep 30
            echo "📊 최근 로그 확인 중..."
            aws logs filter-log-events \
                --log-group-name "/ecs/bitcoin-auto-trader" \
                --start-time $(date -d '5 minutes ago' +%s)000 \
                --query 'events[*].message' \
                --output text | head -20
                
        else
            echo "❌ 태스크 시작 실패"
            exit 1
        fi
        
    else
        echo "❌ 활성 태스크 정의를 찾을 수 없습니다: $TASK_FAMILY"
        exit 1
    fi
    
else
    echo "❌ ECS 클러스터를 찾을 수 없습니다: $CLUSTER_NAME"
    echo "💡 먼저 인프라를 배포해야 합니다."
    exit 1
fi

echo ""
echo "🎉 시크릿 업데이트 및 테스트 완료!"
echo "📈 이제 10분마다 자동으로 거래 봇이 실행됩니다."
echo "📧 알림을 받으려면 SNS 토픽에 이메일을 구독하세요:"

# SNS 토픽 찾기
SNS_TOPIC_ARN=$(aws sns list-topics --query 'Topics[?contains(TopicArn, `bitcoin-auto-trader`) || contains(TopicArn, `alerts`)].TopicArn' --output text | head -1)
if [ -n "$SNS_TOPIC_ARN" ]; then
    echo "aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com"
fi

echo ""
echo "🛠️ 관리 명령어:"
echo "  # 스케줄 일시정지"
echo "  aws events disable-rule --name bitcoin-auto-trader-schedule"
echo "  # 스케줄 재시작"
echo "  aws events enable-rule --name bitcoin-auto-trader-schedule"