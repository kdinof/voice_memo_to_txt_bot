#!/bin/bash

# Voice Memo Bot - Database Backup Script
# Usage: ./backup.sh [backup_name]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🗄️ Voice Memo Bot - Database Backup${NC}"
echo "===================================="

# Check if we're in the right directory
if [[ ! -f "docker-compose.prod.yml" ]]; then
    echo -e "${RED}❌ Error: docker-compose.prod.yml not found${NC}"
    echo "Please run this script from the project directory"
    exit 1
fi

# Check if production container is running
CONTAINER_NAME="voice-memo-bot-prod"
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${YELLOW}⚠️ Warning: Production container is not running${NC}"
    echo "The backup will only include data from the Docker volume"
fi

# Generate backup filename
if [ -z "$1" ]; then
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S).db"
else
    BACKUP_NAME="$1.db"
fi

# Create backups directory if it doesn't exist
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}📋 Backup Information:${NC}"
echo "  Container: $CONTAINER_NAME"
echo "  Volume: voice_memo_to_txt_bot_bot_data_prod"
echo "  Backup file: $BACKUP_DIR/$BACKUP_NAME"
echo

# Create backup from Docker volume
echo -e "${BLUE}💾 Creating database backup...${NC}"

# Method 1: If container is running, copy from running container
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${BLUE}📤 Copying from running container...${NC}"
    docker exec "$CONTAINER_NAME" cp /home/app/data/bot_users.db /tmp/backup_temp.db
    docker cp "$CONTAINER_NAME:/tmp/backup_temp.db" "$BACKUP_DIR/$BACKUP_NAME"
    docker exec "$CONTAINER_NAME" rm /tmp/backup_temp.db
else
    # Method 2: If container is not running, access volume directly
    echo -e "${BLUE}📤 Copying from Docker volume...${NC}"
    docker run --rm \
        -v voice_memo_to_txt_bot_bot_data_prod:/source:ro \
        -v "$(pwd)/$BACKUP_DIR":/backup \
        alpine cp /source/bot_users.db "/backup/$BACKUP_NAME"
fi

# Verify backup was created
if [[ -f "$BACKUP_DIR/$BACKUP_NAME" ]]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
    echo -e "${GREEN}✅ Backup created successfully!${NC}"
    echo -e "${GREEN}   File: $BACKUP_DIR/$BACKUP_NAME${NC}"
    echo -e "${GREEN}   Size: $BACKUP_SIZE${NC}"
else
    echo -e "${RED}❌ Backup failed - file not created${NC}"
    exit 1
fi

# Verify backup integrity (check if it's a valid SQLite database)
echo -e "${BLUE}🔍 Verifying backup integrity...${NC}"
if sqlite3 "$BACKUP_DIR/$BACKUP_NAME" "SELECT name FROM sqlite_master WHERE type='table';" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backup integrity verified - valid SQLite database${NC}"
    
    # Show backup statistics
    echo -e "${BLUE}📊 Database Statistics:${NC}"
    USERS_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "N/A")
    USAGE_LOGS_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME" "SELECT COUNT(*) FROM usage_logs;" 2>/dev/null || echo "N/A")
    PRO_USERS_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME" "SELECT COUNT(*) FROM users WHERE is_pro=1;" 2>/dev/null || echo "N/A")
    
    echo "  Total users: $USERS_COUNT"
    echo "  PRO users: $PRO_USERS_COUNT"
    echo "  Usage logs: $USAGE_LOGS_COUNT"
else
    echo -e "${RED}❌ Warning: Backup may be corrupted - not a valid SQLite database${NC}"
    exit 1
fi

# Show all backups
echo -e "${BLUE}📁 Available Backups:${NC}"
if ls "$BACKUP_DIR"/*.db > /dev/null 2>&1; then
    ls -lah "$BACKUP_DIR"/*.db | while read line; do
        echo "  $line"
    done
else
    echo "  No backups found"
fi

echo
echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
echo -e "${BLUE}💡 Restore Instructions:${NC}"
echo "  1. Stop bot: docker-compose -f docker-compose.prod.yml down"
echo "  2. Restore: docker run --rm -v voice_memo_to_txt_bot_bot_data_prod:/data -v \$(pwd)/$BACKUP_DIR:/backup alpine cp /backup/$BACKUP_NAME /data/bot_users.db"
echo "  3. Start bot: docker-compose -f docker-compose.prod.yml up -d"
echo
echo -e "${YELLOW}💾 Consider uploading backups to cloud storage for extra safety!${NC}"