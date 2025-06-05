#!/bin/bash

# 기존 AWS 리소스들을 Terraform state로 import하는 스크립트

set -e

echo "🔄 기존 AWS 리소스를 Terraform state로 import합니다..."

# 현재 AWS 계정 ID와 리전 가져오기
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
REGION=$(aws configure get region)

echo "📍 Account ID: $ACCOUNT_ID"
echo "📍 Region: $REGION"

# ECR Repository import
echo "📦 ECR Repository import 시도..."
if aws ecr describe-repositories --repository-names bitcoin-auto-trader --region $REGION >/dev/null 2>&1; then
    echo "✅ ECR Repository 'bitcoin-auto-trader' 발견됨"
    terraform import aws_ecr_repository.bitcoin_trading bitcoin-auto-trader || echo "⚠️ ECR Repository import 실패 (이미 존재할 수 있음)"
else
    echo "❌ ECR Repository 'bitcoin-auto-trader' 존재하지 않음"
fi

# S3 Bucket import
BUCKET_NAME="bitcoin-auto-trader-state-${ACCOUNT_ID}-${REGION}"
echo "🪣 S3 Bucket import 시도: $BUCKET_NAME"
if aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION >/dev/null 2>&1; then
    echo "✅ S3 Bucket '$BUCKET_NAME' 발견됨"
    terraform import aws_s3_bucket.trading_state $BUCKET_NAME || echo "⚠️ S3 Bucket import 실패 (이미 존재할 수 있음)"
else
    echo "❌ S3 Bucket '$BUCKET_NAME' 존재하지 않음"
fi

# CloudWatch Log Group import
LOG_GROUP="/ecs/bitcoin-auto-trader"
echo "📊 CloudWatch Log Group import 시도: $LOG_GROUP"
if aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP --region $REGION | grep -q $LOG_GROUP; then
    echo "✅ CloudWatch Log Group '$LOG_GROUP' 발견됨"
    terraform import aws_cloudwatch_log_group.bitcoin_trading $LOG_GROUP || echo "⚠️ CloudWatch Log Group import 실패 (이미 존재할 수 있음)"
else
    echo "❌ CloudWatch Log Group '$LOG_GROUP' 존재하지 않음"
fi

# ECS Cluster import
CLUSTER_NAME="bitcoin-auto-trader-cluster"
echo "🚀 ECS Cluster import 시도: $CLUSTER_NAME"
if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $REGION | grep -q $CLUSTER_NAME; then
    echo "✅ ECS Cluster '$CLUSTER_NAME' 발견됨"
    terraform import aws_ecs_cluster.bitcoin_trading $CLUSTER_NAME || echo "⚠️ ECS Cluster import 실패 (이미 존재할 수 있음)"
else
    echo "❌ ECS Cluster '$CLUSTER_NAME' 존재하지 않음"
fi

# IAM Role imports
echo "🔐 IAM Role import 시도..."

# ECS Execution Role
EXEC_ROLE="bitcoin-auto-trader-ecs-execution-role"
if aws iam get-role --role-name $EXEC_ROLE --region $REGION >/dev/null 2>&1; then
    echo "✅ IAM Role '$EXEC_ROLE' 발견됨"
    terraform import aws_iam_role.ecs_execution_role $EXEC_ROLE || echo "⚠️ IAM Role import 실패 (이미 존재할 수 있음)"
else
    echo "❌ IAM Role '$EXEC_ROLE' 존재하지 않음"
fi

# ECS Task Role
TASK_ROLE="bitcoin-auto-trader-ecs-task-role"
if aws iam get-role --role-name $TASK_ROLE --region $REGION >/dev/null 2>&1; then
    echo "✅ IAM Role '$TASK_ROLE' 발견됨"
    terraform import aws_iam_role.ecs_task_role $TASK_ROLE || echo "⚠️ IAM Role import 실패 (이미 존재할 수 있음)"
else
    echo "❌ IAM Role '$TASK_ROLE' 존재하지 않음"
fi

# EventBridge Role
EVENTBRIDGE_ROLE="bitcoin-auto-trader-eventbridge-role"
if aws iam get-role --role-name $EVENTBRIDGE_ROLE --region $REGION >/dev/null 2>&1; then
    echo "✅ IAM Role '$EVENTBRIDGE_ROLE' 발견됨"
    terraform import aws_iam_role.eventbridge_role $EVENTBRIDGE_ROLE || echo "⚠️ IAM Role import 실패 (이미 존재할 수 있음)"
else
    echo "❌ IAM Role '$EVENTBRIDGE_ROLE' 존재하지 않음"
fi

# Security Group import
echo "🛡️ Security Group import 시도..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)
SG_NAME="bitcoin-auto-trader-ecs-tasks"

SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text --region $REGION 2>/dev/null || echo "None")

if [ "$SG_ID" != "None" ] && [ "$SG_ID" != "null" ]; then
    echo "✅ Security Group '$SG_NAME' 발견됨 (ID: $SG_ID)"
    terraform import aws_security_group.ecs_tasks $SG_ID || echo "⚠️ Security Group import 실패 (이미 존재할 수 있음)"
else
    echo "❌ Security Group '$SG_NAME' 존재하지 않음"
fi

# SNS Topic import
echo "📧 SNS Topic import 시도..."
SNS_TOPIC_NAME="bitcoin-auto-trader-alerts"
SNS_TOPIC_ARN="arn:aws:sns:${REGION}:${ACCOUNT_ID}:${SNS_TOPIC_NAME}"

if aws sns get-topic-attributes --topic-arn $SNS_TOPIC_ARN --region $REGION >/dev/null 2>&1; then
    echo "✅ SNS Topic '$SNS_TOPIC_NAME' 발견됨"
    terraform import aws_sns_topic.trading_alerts $SNS_TOPIC_ARN || echo "⚠️ SNS Topic import 실패 (이미 존재할 수 있음)"
else
    echo "❌ SNS Topic '$SNS_TOPIC_NAME' 존재하지 않음"
fi

# EventBridge Rule import
echo "⏰ EventBridge Rule import 시도..."
RULE_NAME="bitcoin-auto-trader-schedule"
if aws events describe-rule --name $RULE_NAME --region $REGION >/dev/null 2>&1; then
    echo "✅ EventBridge Rule '$RULE_NAME' 발견됨"
    terraform import aws_cloudwatch_event_rule.bitcoin_trading_schedule $RULE_NAME || echo "⚠️ EventBridge Rule import 실패 (이미 존재할 수 있음)"
else
    echo "❌ EventBridge Rule '$RULE_NAME' 존재하지 않음"
fi

# Secrets Manager Secret import
echo "🔑 Secrets Manager Secret import 시도..."
SECRET_NAME="bitcoin-auto-trader/binance"
SECRET_ARN="arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_NAME}"

# Secrets Manager는 실제 이름에 suffix가 붙으므로 list로 찾아야 합니다
SECRET_REAL_ARN=$(aws secretsmanager list-secrets --filters Key="name",Values="$SECRET_NAME" --query 'SecretList[0].ARN' --output text --region $REGION 2>/dev/null || echo "None")

if [ "$SECRET_REAL_ARN" != "None" ] && [ "$SECRET_REAL_ARN" != "null" ]; then
    echo "✅ Secrets Manager Secret '$SECRET_NAME' 발견됨"
    terraform import aws_secretsmanager_secret.binance_credentials $SECRET_REAL_ARN || echo "⚠️ Secrets Manager Secret import 실패 (이미 존재할 수 있음)"
else
    echo "❌ Secrets Manager Secret '$SECRET_NAME' 존재하지 않음"
fi

echo ""
echo "🎉 기존 리소스 import 과정이 완료되었습니다."
echo "⚠️ 일부 리소스가 이미 Terraform state에 있거나 존재하지 않을 수 있습니다."
echo "📋 다음 명령어로 현재 state를 확인하세요: terraform state list" 