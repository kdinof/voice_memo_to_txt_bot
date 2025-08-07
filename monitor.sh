#!/bin/bash

# Voice Memo Bot - Production Monitoring Script
# Usage: ./monitor.sh [command]
# Commands: status, logs, stats, health, restart, update

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

CONTAINER_NAME="voice-memo-bot-prod"
COMPOSE_FILE="docker-compose.prod.yml"

# Function to check if container exists
check_container() {
    if ! docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}❌ Container '${CONTAINER_NAME}' not found${NC}"
        echo "Run './deploy.sh' to deploy the bot first"
        exit 1
    fi
}

# Function to display header
show_header() {
    echo -e "${BLUE}🤖 Voice Memo Bot - Production Monitor${NC}"
    echo "======================================"
    echo
}

# Function to show container status
show_status() {
    echo -e "${CYAN}📊 Container Status:${NC}"
    if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}✅ Running${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}" | grep "$CONTAINER_NAME"
    else
        echo -e "${RED}❌ Stopped${NC}"
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}" | grep "$CONTAINER_NAME"
    fi
    echo
}

# Function to show health status
show_health() {
    echo -e "${CYAN}🏥 Health Status:${NC}"
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "no-healthcheck")
    
    case $HEALTH_STATUS in
        "healthy")
            echo -e "${GREEN}✅ Healthy${NC}"
            ;;
        "unhealthy")
            echo -e "${RED}❌ Unhealthy${NC}"
            echo -e "${YELLOW}Last health check logs:${NC}"
            docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' "$CONTAINER_NAME" | tail -3
            ;;
        "starting")
            echo -e "${YELLOW}🔄 Starting (health check in progress)${NC}"
            ;;
        *)
            echo -e "${YELLOW}⚠️ No health check configured${NC}"
            ;;
    esac
    echo
}

# Function to show resource stats
show_stats() {
    echo -e "${CYAN}📈 Resource Usage:${NC}"
    if docker ps | grep -q "$CONTAINER_NAME"; then
        docker stats "$CONTAINER_NAME" --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    else
        echo -e "${YELLOW}⚠️ Container not running${NC}"
    fi
    echo
}

# Function to show recent logs
show_logs() {
    echo -e "${CYAN}📝 Recent Logs (last 50 lines):${NC}"
    echo "================================"
    docker-compose -f "$COMPOSE_FILE" logs --tail=50 voice-memo-bot
    echo
}

# Function to show database stats
show_db_stats() {
    echo -e "${CYAN}🗄️ Database Statistics:${NC}"
    if docker ps | grep -q "$CONTAINER_NAME"; then
        docker exec "$CONTAINER_NAME" python -c "
import sqlite3
try:
    conn = sqlite3.connect('/home/app/data/bot_users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_pro = 1')
    pro_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM usage_logs')
    usage_logs = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(seconds_used) FROM usage_logs')
    total_seconds = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f'  Total users: {total_users}')
    print(f'  PRO users: {pro_users}')
    print(f'  Regular users: {total_users - pro_users}')
    print(f'  Usage logs: {usage_logs}')
    print(f'  Total usage: {total_seconds//3600}h {(total_seconds%3600)//60}m {total_seconds%60}s')
    
except Exception as e:
    print(f'  Error: {e}')
"
    else
        echo -e "${YELLOW}⚠️ Container not running - cannot access database${NC}"
    fi
    echo
}

# Function to show system info
show_system_info() {
    echo -e "${CYAN}💻 System Information:${NC}"
    echo "  Host: $(hostname)"
    echo "  Uptime: $(uptime -p 2>/dev/null || echo 'N/A')"
    echo "  Load: $(uptime | awk -F'load average:' '{ print $2 }' | sed 's/^[ \t]*//')"
    echo "  Memory: $(free -h | awk '/^Mem:/ { print $3 "/" $2 " (" $3/$2*100.0 "%" ")" }')"
    echo "  Disk: $(df -h / | awk 'NR==2 { print $3 "/" $2 " (" $5 ")" }')"
    echo "  Docker: $(docker --version 2>/dev/null || echo 'N/A')"
    echo
}

# Function to restart the bot
restart_bot() {
    echo -e "${YELLOW}🔄 Restarting bot...${NC}"
    docker-compose -f "$COMPOSE_FILE" restart
    echo -e "${GREEN}✅ Bot restarted${NC}"
    echo
    # Wait a moment and show status
    sleep 3
    show_status
}

# Function to update the bot
update_bot() {
    echo -e "${YELLOW}🔄 Updating bot...${NC}"
    
    echo -e "${BLUE}📥 Pulling latest changes...${NC}"
    git pull origin main
    
    echo -e "${BLUE}🔨 Rebuilding and restarting...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d --build
    
    echo -e "${GREEN}✅ Bot updated successfully${NC}"
    echo
    # Wait a moment and show status
    sleep 5
    show_status
}

# Main script logic
case "${1:-status}" in
    "status"|"s")
        show_header
        show_status
        show_health
        ;;
    
    "logs"|"l")
        show_header
        show_logs
        ;;
    
    "stats"|"st")
        show_header
        check_container
        show_stats
        show_db_stats
        ;;
    
    "health"|"h")
        show_header
        check_container
        show_health
        ;;
    
    "full"|"f")
        show_header
        check_container
        show_status
        show_health
        show_stats
        show_db_stats
        show_system_info
        ;;
    
    "restart"|"r")
        show_header
        check_container
        restart_bot
        ;;
    
    "update"|"u")
        show_header
        check_container
        update_bot
        ;;
    
    "live"|"tail")
        echo -e "${CYAN}📺 Live logs (Ctrl+C to exit):${NC}"
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    
    "help"|"--help"|"-h")
        show_header
        echo -e "${CYAN}Available commands:${NC}"
        echo "  status, s    - Show container status and health"
        echo "  logs, l      - Show recent logs"
        echo "  stats, st    - Show resource usage and database stats"
        echo "  health, h    - Show detailed health status"
        echo "  full, f      - Show all information"
        echo "  restart, r   - Restart the bot"
        echo "  update, u    - Update bot to latest version"
        echo "  live, tail   - Follow live logs"
        echo "  help         - Show this help message"
        echo
        echo -e "${CYAN}Usage examples:${NC}"
        echo "  ./monitor.sh"
        echo "  ./monitor.sh status"
        echo "  ./monitor.sh logs"
        echo "  ./monitor.sh full"
        echo
        ;;
    
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo "Use './monitor.sh help' for available commands"
        exit 1
        ;;
esac