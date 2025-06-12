# 🔧 트러블슈팅 가이드

## ❌ 문제: Secrets Manager 접근 권한 오류

### 발생한 오류
```
ResourceInitializationError: unable to pull secrets or registry auth: 
execution resource retrieval failed: unable to retrieve secret from asm: 
service call has been retried 1 time(s): failed to fetch secret 
arn:aws:secretsmanager:ap-northeast-2:205070775242:secret:bitcoin-auto-trader/binance-UMl6GF 
from secrets manager: AccessDeniedException: User: arn:aws:sts::205070775242:assumed-role/bitcoin-auto-trader-ecs-execution-role/259ab992ff9d4af08a4fc104adda511d 
is not authorized to perform: secretsmanager:GetSecretValue
```

### ✅ 해결 방법

#### 1단계: ECS 실행 역할에 Secrets Manager 권한 추가 (완료)
이미 Terraform으로 권한을 추가했습니다:
```bash
# 확인: 
terraform show | grep -A 10 "ecs_execution_secrets_policy"
```

#### 2단계: Binance API 키를 Secrets Manager에 설정
```bash
# 대화형으로 API 키 설정:
./set-secrets.sh
```

또는 직접 명령어로:
```bash
# JSON 형태로 저장 (api_key와 secret 키 모두 포함)
aws secretsmanager put-secret-value \
    --secret-id bitcoin-auto-trader/binance \
    --secret-string '{"api_key":"YOUR_BINANCE_API_KEY","secret":"YOUR_BINANCE_SECRET_KEY"}'
```

#### 3단계: 설정 확인
```bash
# Secret이 올바르게 저장되었는지 확인:
aws secretsmanager describe-secret --secret-id bitcoin-auto-trader/binance

# Secret 값 확인 (마스킹됨):
aws secretsmanager get-secret-value --secret-id bitcoin-auto-trader/binance --query SecretString --output text
```

#### 4단계: ECS 태스크 수동 실행
```bash
# 태스크 실행:
./run-task.sh

# 로그 확인:
./view-logs.sh --follow
```

## 🔍 기타 가능한 문제들

### 문제 1: ECS 태스크가 시작되지 않음
```bash
# 태스크 상태 확인:
aws ecs describe-tasks --cluster bitcoin-auto-trader-cluster --tasks TASK_ARN

# 서비스 이벤트 확인:
aws ecs describe-services --cluster bitcoin-auto-trader-cluster --services bitcoin-auto-trader-service
```

### 문제 2: 컨테이너 이미지가 없음
```bash
# ECR에 이미지 푸시가 필요:
cd .. # 프로젝트 루트로 이동
docker build -t bitcoin-auto-trader .
docker tag bitcoin-auto-trader:latest 205070775242.dkr.ecr.ap-northeast-2.amazonaws.com/bitcoin-auto-trader:latest

# ECR 로그인:
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 205070775242.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 푸시:
docker push 205070775242.dkr.ecr.ap-northeast-2.amazonaws.com/bitcoin-auto-trader:latest
```

### 문제 3: 네트워크 구성 오류
```bash
# 보안 그룹 확인:
aws ec2 describe-security-groups --group-names bitcoin-auto-trader-ecs-tasks

# 서브넷 확인:
aws ec2 describe-subnets --filters "Name=default-for-az,Values=true"
```

## 📊 모니터링

### CloudWatch 대시보드 확인
```bash
# 메트릭 확인:
aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=bitcoin-auto-trader-service Name=ClusterName,Value=bitcoin-auto-trader-cluster \
    --start-time $(date -d '1 hour ago' --iso-8601) \
    --end-time $(date --iso-8601) \
    --period 300 \
    --statistics Average
```

### 알림 설정 확인
```bash
# SNS 토픽 구독 확인:
aws sns list-subscriptions-by-topic --topic-arn $(terraform output -raw sns_topic_arn)

# 이메일 구독 추가:
aws sns subscribe \
    --topic-arn $(terraform output -raw sns_topic_arn) \
    --protocol email \
    --notification-endpoint your-email@example.com
```

## 🛠️ 유용한 스크립트들

### 모든 로그 확인
```bash
./view-logs.sh              # 최근 30분 로그
./view-logs.sh --recent     # 최근 1시간 로그  
./view-logs.sh --errors     # 에러 로그만
./view-logs.sh --follow     # 실시간 로그
```

### 태스크 관리
```bash
./run-task.sh               # 태스크 수동 실행
./set-secrets.sh            # API 키 설정
```

### 인프라 확인
```bash
terraform output            # 모든 출력값 확인
terraform show              # 현재 상태 확인
terraform plan              # 변경사항 확인
```

## 📞 추가 도움이 필요한 경우

1. **AWS 콘솔에서 직접 확인**:
   - ECS 클러스터: https://ap-northeast-2.console.aws.amazon.com/ecs/home?region=ap-northeast-2#/clusters
   - CloudWatch 로그: https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups
   - Secrets Manager: https://ap-northeast-2.console.aws.amazon.com/secretsmanager/home?region=ap-northeast-2

2. **로그 분석**: 
   - `./view-logs.sh --errors`로 에러 로그 확인
   - ECS 태스크 상세 페이지에서 이벤트 탭 확인

3. **비용 최적화**:
   - EventBridge 스케줄러가 10분마다 실행되므로 불필요한 실행 방지
   - 개발 중에는 `terraform destroy`로 리소스 삭제 후 재생성 