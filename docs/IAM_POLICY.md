# AWS IAM 권한 설정 가이드

이 문서는 비트코인 자동거래 봇을 AWS에 배포하기 위해 필요한 IAM 권한을 설명합니다.

## 📋 필요한 AWS 서비스

배포 과정에서 다음 AWS 서비스들이 사용됩니다:

- **AWS Lambda**: 트레이딩 봇 실행
- **Amazon S3**: 거래 상태 저장
- **Amazon DynamoDB**: 거래 상태 저장 (대안)
- **Amazon SNS**: 알림 발송
- **Amazon CloudWatch**: 로그 및 모니터링
- **Amazon EventBridge**: 스케줄링
- **AWS CloudFormation**: 인프라 배포
- **AWS IAM**: 권한 관리

## 🔐 최소 필요 권한 (Minimal IAM Policy)

배포를 위해 최소한으로 필요한 권한들입니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaPermissions",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:DeleteFunction",
                "lambda:GetFunction",
                "lambda:ListFunctions",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:InvokeFunction",
                "lambda:PublishLayerVersion",
                "lambda:DeleteLayerVersion"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3Permissions",
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketPolicy",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetBucketVersioning",
                "s3:PutBucketVersioning"
            ],
            "Resource": [
                "arn:aws:s3:::bitcoin-auto-trader-*",
                "arn:aws:s3:::bitcoin-auto-trader-*/*"
            ]
        },
        {
            "Sid": "DynamoDBPermissions",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/bitcoin-auto-trader-*"
        },
        {
            "Sid": "SNSPermissions",
            "Effect": "Allow",
            "Action": [
                "sns:CreateTopic",
                "sns:DeleteTopic",
                "sns:GetTopicAttributes",
                "sns:SetTopicAttributes",
                "sns:Subscribe",
                "sns:Unsubscribe",
                "sns:Publish",
                "sns:ListTopics"
            ],
            "Resource": "arn:aws:sns:*:*:bitcoin-auto-trader-*"
        },
        {
            "Sid": "CloudWatchPermissions",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:DeleteLogGroup"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/bitcoin-auto-trader-*"
        },
        {
            "Sid": "EventBridgePermissions",
            "Effect": "Allow",
            "Action": [
                "events:PutRule",
                "events:DeleteRule",
                "events:DescribeRule",
                "events:PutTargets",
                "events:RemoveTargets",
                "events:ListRules",
                "events:ListTargetsByRule"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudFormationPermissions",
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateStack",
                "cloudformation:UpdateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "cloudformation:ValidateTemplate",
                "cloudformation:ListStacks",
                "cloudformation:ListStackResources"
            ],
            "Resource": "arn:aws:cloudformation:*:*:stack/bitcoin-auto-trader-*/*"
        },
        {
            "Sid": "IAMPermissions",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/bitcoin-auto-trader-*",
                "arn:aws:iam::*:policy/bitcoin-auto-trader-*"
            ]
        }
    ]
}
```

## 🚀 관리자 권한 (권장)

개발 및 테스트 단계에서는 관리자 권한 사용을 권장합니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*"
        }
    ]
}
```

## 🛡️ 보안 고려사항

### 1. 프로덕션 환경

프로덕션 환경에서는 최소 권한 원칙을 적용하세요:

- 리소스 ARN을 구체적으로 지정
- 불필요한 권한 제거
- 정기적인 권한 검토

### 2. IAM 사용자 vs IAM 역할

**GitHub Actions용 IAM 사용자 생성:**

```bash
# IAM 사용자 생성
aws iam create-user --user-name bitcoin-trader-deployer

# 정책 연결
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 액세스 키 생성
aws iam create-access-key --user-name bitcoin-trader-deployer
```

### 3. 정책 적용 방법

**방법 1: 직접 정책 생성**

```bash
# 정책 파일 생성 (위의 JSON을 파일로 저장)
aws iam create-policy \
    --policy-name BitcoinTraderDeployPolicy \
    --policy-document file://minimal-policy.json

# 사용자에게 정책 연결
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::ACCOUNT-ID:policy/BitcoinTraderDeployPolicy
```

**방법 2: 관리형 정책 사용**

```bash
# AdministratorAccess 정책 연결 (개발용)
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

## 🔍 권한 검증

배포 전 권한이 올바르게 설정되었는지 확인:

```bash
# 현재 사용자 정보 확인
aws sts get-caller-identity

# Lambda 함수 목록 조회 (권한 테스트)
aws lambda list-functions

# S3 버킷 목록 조회 (권한 테스트)
aws s3 ls

# CloudFormation 스택 목록 조회 (권한 테스트)
aws cloudformation list-stacks
```

## ⚠️ 주의사항

1. **액세스 키 보안**: GitHub Secrets에 저장하고 코드에 하드코딩하지 마세요
2. **권한 최소화**: 프로덕션에서는 필요한 권한만 부여하세요  
3. **정기 검토**: 사용하지 않는 권한은 정기적으로 제거하세요
4. **MFA 활성화**: 중요한 계정에는 MFA를 활성화하세요

## 🔧 트러블슈팅

### 배포 실패 시 확인사항

1. **권한 부족 오류**:
   ```
   User: arn:aws:iam::123456789012:user/deployer is not authorized to perform: lambda:CreateFunction
   ```
   → Lambda 관련 권한 추가 필요

2. **리소스 접근 거부**:
   ```
   Access Denied when calling the PutObject operation
   ```
   → S3 권한 확인 필요

3. **CloudFormation 오류**:
   ```
   User is not authorized to perform: cloudformation:CreateStack
   ```
   → CloudFormation 권한 추가 필요

### 권한 디버깅

```bash
# CloudTrail로 API 호출 이력 확인
aws logs filter-log-events \
    --log-group-name CloudTrail/APILogs \
    --filter-pattern "{ $.errorCode = \"*\" }"

# IAM 정책 시뮬레이터 사용
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::123456789012:user/deployer \
    --action-names lambda:CreateFunction \
    --resource-arns '*'
``` 