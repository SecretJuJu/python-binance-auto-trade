#!/bin/bash

# ECS 태스크 수동 실행 스크립트
# 사용법: ./run-task.sh

set -e

echo "🚀 비트코인 자동거래 봇 ECS 태스크를 실행합니다..."

# Terraform 출력에서 필요한 값들 가져오기
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
TASK_DEFINITION=$(terraform output -raw task_definition_arn | cut -d'/' -f2)

# 기본 VPC 서브넷과 보안 그룹 가져오기
SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=default-for-az,Values=true" \
    --query 'Subnets[0].SubnetId' \
    --output text)

SECURITY_GROUP=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=bitcoin-auto-trader-ecs-tasks" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

echo "📋 설정 정보:"
echo "  - Cluster: $CLUSTER_NAME"
echo "  - Task Definition: $TASK_DEFINITION"
echo "  - Subnet: $SUBNETS"
echo "  - Security Group: $SECURITY_GROUP"
echo ""

# ECS 태스크 실행
echo "▶️  태스크를 실행합니다..."
TASK_ARN=$(aws ecs run-task \
    --cluster "$CLUSTER_NAME" \
    --task-definition "$TASK_DEFINITION" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
    --query 'tasks[0].taskArn' \
    --output text)

if [ $? -eq 0 ]; then
    echo "✅ 태스크가 성공적으로 시작되었습니다!"
    echo "📄 Task ARN: $TASK_ARN"
    echo ""
    
    # 태스크 상태 확인
    echo "⏳ 태스크 상태를 확인합니다..."
    sleep 5
    
    TASK_STATUS=$(aws ecs describe-tasks \
        --cluster "$CLUSTER_NAME" \
        --tasks "$TASK_ARN" \
        --query 'tasks[0].lastStatus' \
        --output text)
    
    echo "📊 현재 상태: $TASK_STATUS"
    
    # 로그 그룹 안내
    echo ""
    echo "📝 로그를 확인하려면 다음 명령어를 사용하세요:"
    echo "aws logs tail /ecs/bitcoin-auto-trader --follow"
    echo ""
    echo "🌐 AWS 콘솔에서도 확인 가능합니다:"
    echo "https://ap-northeast-2.console.aws.amazon.com/ecs/home?region=ap-northeast-2#/clusters/$CLUSTER_NAME/tasks"
    
else
    echo "❌ 태스크 실행에 실패했습니다."
    exit 1
fi 