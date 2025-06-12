#!/bin/bash

# CloudWatch 로그 확인 스크립트
# 사용법: ./view-logs.sh [옵션]
# 옵션: --follow (실시간 로그), --recent (최근 1시간), --errors (에러만)

set -e

LOG_GROUP="/ecs/bitcoin-auto-trader"

# 도움말 함수
show_help() {
    echo "🔍 CloudWatch 로그 확인 스크립트"
    echo ""
    echo "사용법:"
    echo "  ./view-logs.sh           # 최근 로그 확인"
    echo "  ./view-logs.sh --follow  # 실시간 로그 추적"
    echo "  ./view-logs.sh --recent  # 최근 1시간 로그"
    echo "  ./view-logs.sh --errors  # 에러 로그만 필터링"
    echo "  ./view-logs.sh --help    # 도움말"
    echo ""
}

# 인수 처리
case "${1:-}" in
    --help)
        show_help
        exit 0
        ;;
    --follow)
        echo "📡 실시간 로그를 추적합니다... (Ctrl+C로 종료)"
        aws logs tail "$LOG_GROUP" --follow
        ;;
    --recent)
        echo "🕐 최근 1시간의 로그를 확인합니다..."
        aws logs filter-log-events \
            --log-group-name "$LOG_GROUP" \
            --start-time $(date -d '1 hour ago' +%s)000 \
            --output table
        ;;
    --errors)
        echo "❌ 에러 로그를 확인합니다..."
        aws logs filter-log-events \
            --log-group-name "$LOG_GROUP" \
            --filter-pattern "ERROR" \
            --start-time $(date -d '1 day ago' +%s)000 \
            --output table
        ;;
    "")
        echo "📋 최근 로그를 확인합니다..."
        aws logs tail "$LOG_GROUP" --since 30m
        ;;
    *)
        echo "❌ 알 수 없는 옵션: $1"
        show_help
        exit 1
        ;;
esac 