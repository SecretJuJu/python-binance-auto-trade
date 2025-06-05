# 🔄 마이그레이션 요약: Lambda → Terraform + ECS Fargate

## 📋 변경 사항 개요

기존의 Lambda + Serverless Framework 기반에서 **Terraform + ECS Fargate** 기반으로 완전히 전환했습니다.

### 🗑️ 제거된 파일들

- `serverless.yml` - Serverless Framework 설정
- `lambda_handler.py` - Lambda 핸들러
- `cdk/` 디렉토리 전체 - AWS CDK 관련 파일들
- `deploy-fargate.sh` - 기존 CDK 기반 배포 스크립트

### 🆕 추가된 파일들

```
terraform/
├── main.tf                    # 메인 인프라 정의 (ECS, ECR, S3, SNS 등)
├── variables.tf               # 입력 변수 정의
├── outputs.tf                 # 출력값 정의
├── security.tf                # 보안 그룹 정의
├── secrets.tf                 # Secrets Manager 설정
├── terraform.tfvars.example   # 변수 파일 예시
└── .gitignore                 # Terraform 전용 gitignore

deploy-terraform.sh            # Terraform 기반 배포 스크립트
destroy.sh                     # 인프라 삭제 스크립트
docs/TERRAFORM_DEPLOYMENT.md   # Terraform 배포 가이드
```

### 🔄 수정된 파일들

- **README.md**: 전체 가이드를 Terraform 기반으로 업데이트
- **package.json**: npm scripts를 Terraform 명령어로 변경
- **.gitignore**: Terraform 관련 파일 제외 규칙 추가
- **fargate_main.py**: 기존 파일 유지 (이미 Fargate용으로 구성됨)

## 🏗️ 아키텍처 변경 사항

### Before (Lambda + Serverless)
```
EventBridge (5분) → Lambda Function → S3/DynamoDB + SNS
```

### After (Terraform + ECS Fargate)
```
EventBridge (10분) → ECS Fargate Task (0개 유지) → S3 + SNS
                     ↓
                   컨테이너 자동 종료 (비용 최적화)
```

## 🚀 배포 방법 변경

### Before
```bash
npm run deploy        # Serverless Framework
./deploy-fargate.sh   # CDK 기반
```

### After
```bash
./deploy-terraform.sh  # Terraform 기반 (권장)

# 또는 수동
cd terraform
terraform init
terraform plan
terraform apply
```

## 💰 비용 영향

| 항목 | Before (Lambda) | After (Fargate) | 변화 |
|------|----------------|----------------|------|
| 실행 주기 | 5분마다 | 10분마다 | 50% 감소 |
| 컴퓨팅 비용 | ~$1.50/월 | ~$2.50/월 | +67% |
| 라이브러리 제한 | 250MB 제한 | 제한 없음 | 🎉 |
| 총 예상 비용 | ~$2.50/월 | ~$3.61/월 | +44% |

**주요 장점**: 
- 라이브러리 크기 제한 해결 (pandas, numpy 등 자유롭게 사용 가능)
- 컨테이너 기반으로 더 안정적인 환경
- 로컬과 동일한 실행 환경

## 📊 주요 개선 사항

### 1. 라이브러리 제한 해결
- **Before**: Lambda Layer 250MB 제한으로 pandas 제거 필요
- **After**: 모든 라이브러리 자유롭게 사용 가능

### 2. 인프라 관리
- **Before**: Serverless Framework + CDK 혼용
- **After**: Terraform 단일 도구로 통합

### 3. 스케줄링
- **Before**: 5분마다 실행
- **After**: 10분마다 실행 (API 호출 부담 감소)

### 4. 컨테이너 최적화
- **Before**: Lambda cold start 이슈
- **After**: 필요시에만 컨테이너 실행, 완료 후 자동 종료

## 🔧 관리 명령어 변경

### 로그 확인
```bash
# Before
npm run logs

# After  
npm run logs
aws logs tail /ecs/bitcoin-auto-trader --follow
```

### 수동 실행
```bash
# Before
npm run invoke

# After
npm run task:run
```

### 스케줄 관리
```bash
# Before
(Serverless Framework 설정 변경 필요)

# After
npm run schedule:disable  # 일시 중지
npm run schedule:enable   # 재개
```

### 인프라 삭제
```bash
# Before
npm run remove

# After
npm run destroy
./destroy.sh
```

## 🛡️ 보안 강화

### 1. Secrets Manager 사용
- **Before**: 환경 변수로 API 키 전달
- **After**: AWS Secrets Manager로 안전한 저장

### 2. 최소 권한 IAM
- **Before**: 과도한 권한 부여 가능성
- **After**: 명시적인 최소 권한 정의

### 3. 네트워크 보안
- **Before**: Lambda 기본 네트워크
- **After**: 전용 보안 그룹으로 아웃바운드만 허용

## 📈 모니터링 개선

### CloudWatch 로그
- **Before**: `/aws/lambda/function-name`
- **After**: `/ecs/bitcoin-auto-trader`

### 메트릭
- ECS 클러스터 및 태스크 메트릭 추가
- 컨테이너 수준의 세밀한 모니터링

## 🎯 마이그레이션 완료 체크리스트

- [x] 기존 Lambda/CDK 파일 제거
- [x] Terraform 인프라 정의 완료
- [x] ECS Fargate 태스크 설정 완료
- [x] EventBridge 스케줄링 설정 (10분)
- [x] S3 상태 저장 구성
- [x] SNS 알림 시스템 구성
- [x] Secrets Manager 설정
- [x] 보안 그룹 설정
- [x] 배포/삭제 스크립트 작성
- [x] 문서 업데이트 완료
- [x] npm scripts 업데이트

## 🚀 다음 단계

1. **환경 변수 설정**:
   ```bash
   export BINANCE_API_KEY="your_api_key"
   export BINANCE_SECRET="your_secret"
   ```

2. **배포 실행**:
   ```bash
   ./deploy-terraform.sh
   ```

3. **이메일 알림 설정**:
   ```bash
   SNS_TOPIC_ARN=$(cd terraform && terraform output -raw sns_topic_arn)
   aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com
   ```

4. **모니터링 시작**:
   ```bash
   npm run logs
   ```

---

**마이그레이션이 완료되었습니다! 🎉**

이제 Terraform을 사용한 완전히 자동화된 ECS Fargate 기반의 비트코인 자동거래 시스템을 사용할 수 있습니다.
크기 제한 없이 모든 라이브러리를 자유롭게 사용하면서도 비용 효율적인 서버리스 환경을 구축했습니다. 