#!/bin/bash

# Voice Memo Bot - Health Check Script
# This script can be used for external monitoring (cron, monitoring services, etc.)
# Exit codes: 0 = healthy, 1 = unhealthy, 2 = critical

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CONTAINER_NAME="voice-memo-bot-prod"
CRITICAL_MEMORY_THRESHOLD=90  # Percentage
CRITICAL_CPU_THRESHOLD=90     # Percentage

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if container is running
check_container_running() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log "❌ CRITICAL: Container is not running"
        return 2
    fi
    return 0
}

# Function to check container health
check_container_health() {
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "no-healthcheck")
    
    case $health_status in
        "healthy")
            log "✅ Health check: Healthy"
            return 0
            ;;
        "unhealthy")
            log "❌ CRITICAL: Health check failed"
            return 2
            ;;
        "starting")
            log "⚠️ WARNING: Health check still starting"
            return 1
            ;;
        *)
            log "⚠️ WARNING: No health check configured"
            return 1
            ;;
    esac
}

# Function to check resource usage
check_resource_usage() {
    local stats=$(docker stats "$CONTAINER_NAME" --no-stream --format "{{.CPUPerc}} {{.MemPerc}}")
    local cpu_percent=$(echo $stats | cut -d' ' -f1 | sed 's/%//')
    local mem_percent=$(echo $stats | cut -d' ' -f2 | sed 's/%//')
    
    local return_code=0
    
    # Check CPU usage
    if (( $(echo "$cpu_percent > $CRITICAL_CPU_THRESHOLD" | bc -l) )); then
        log "❌ CRITICAL: High CPU usage: ${cpu_percent}%"
        return_code=2
    elif (( $(echo "$cpu_percent > 70" | bc -l) )); then
        log "⚠️ WARNING: Elevated CPU usage: ${cpu_percent}%"
        return_code=1
    else
        log "✅ CPU usage normal: ${cpu_percent}%"
    fi
    
    # Check memory usage
    if (( $(echo "$mem_percent > $CRITICAL_MEMORY_THRESHOLD" | bc -l) )); then
        log "❌ CRITICAL: High memory usage: ${mem_percent}%"
        return_code=2
    elif (( $(echo "$mem_percent > 70" | bc -l) )); then
        log "⚠️ WARNING: Elevated memory usage: ${mem_percent}%"
        [ $return_code -eq 0 ] && return_code=1
    else
        log "✅ Memory usage normal: ${mem_percent}%"
    fi
    
    return $return_code
}

# Function to check database connectivity
check_database() {
    local db_check=$(docker exec "$CONTAINER_NAME" python -c "
import sqlite3
try:
    conn = sqlite3.connect('/home/app/data/bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    conn.close()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null)

    if [[ "$db_check" == "OK" ]]; then
        log "✅ Database connectivity: OK"
        return 0
    else
        log "❌ CRITICAL: Database connectivity failed: $db_check"
        return 2
    fi
}

# Function to check disk space
check_disk_space() {
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if (( disk_usage > 90 )); then
        log "❌ CRITICAL: Low disk space: ${disk_usage}% used"
        return 2
    elif (( disk_usage > 80 )); then
        log "⚠️ WARNING: Disk space getting low: ${disk_usage}% used"
        return 1
    else
        log "✅ Disk space OK: ${disk_usage}% used"
        return 0
    fi
}

# Function to check recent errors in logs
check_recent_errors() {
    local error_count=$(docker logs "$CONTAINER_NAME" --since="5m" 2>&1 | grep -i "error\|exception\|failed\|critical" | wc -l)
    
    if (( error_count > 5 )); then
        log "❌ CRITICAL: High error rate: $error_count errors in last 5 minutes"
        return 2
    elif (( error_count > 2 )); then
        log "⚠️ WARNING: Some errors detected: $error_count errors in last 5 minutes"
        return 1
    else
        log "✅ No recent errors detected"
        return 0
    fi
}

# Main health check
main() {
    log "🏥 Starting health check for $CONTAINER_NAME"
    
    local overall_status=0
    local checks_passed=0
    local checks_warned=0
    local checks_failed=0
    
    # Array of check functions
    checks=(
        "check_container_running"
        "check_container_health"
        "check_resource_usage"
        "check_database"
        "check_disk_space"
        "check_recent_errors"
    )
    
    # Run all checks
    for check in "${checks[@]}"; do
        if $check; then
            ((checks_passed++))
        else
            case $? in
                1)
                    ((checks_warned++))
                    [ $overall_status -eq 0 ] && overall_status=1
                    ;;
                2)
                    ((checks_failed++))
                    overall_status=2
                    ;;
            esac
        fi
    done
    
    # Summary
    log "📊 Health check summary: $checks_passed passed, $checks_warned warnings, $checks_failed failed"
    
    case $overall_status in
        0)
            log "🎉 Overall status: HEALTHY"
            ;;
        1)
            log "⚠️ Overall status: WARNING - Some issues detected"
            ;;
        2)
            log "❌ Overall status: CRITICAL - Immediate attention required"
            ;;
    esac
    
    # Send alert if critical (can be extended to send notifications)
    if [ $overall_status -eq 2 ]; then
        log "🚨 ALERT: Critical issues detected with voice memo bot"
        # Add notification logic here (email, Slack, etc.)
    fi
    
    return $overall_status
}

# Handle script arguments
case "${1:-check}" in
    "check"|"")
        main
        ;;
    "status")
        if check_container_running; then
            echo "RUNNING"
        else
            echo "STOPPED"
        fi
        ;;
    "quick")
        log "🔍 Quick health check"
        check_container_running && check_container_health
        ;;
    "help"|"--help"|"-h")
        echo "Voice Memo Bot Health Check Script"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  check     - Full health check (default)"
        echo "  status    - Check if container is running"
        echo "  quick     - Quick health check (container + health only)"
        echo "  help      - Show this help"
        echo
        echo "Exit codes:"
        echo "  0 = Healthy"
        echo "  1 = Warning (some issues detected)"
        echo "  2 = Critical (immediate attention required)"
        echo
        echo "Example cron entry for monitoring:"
        echo "*/5 * * * * /path/to/health-check.sh >> /var/log/voice-bot-health.log"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac