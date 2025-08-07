#!/bin/bash

# Voice Memo Bot - Production Deployment Script
# Usage: ./deploy.sh [PRODUCTION_BOT_TOKEN]

set -e  # Exit on any error

echo "🚀 Voice Memo Bot - Production Deployment"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please don't run this script as root. Create a regular user first.${NC}"
    echo "Run: adduser botuser && usermod -aG docker botuser && su - botuser"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}⚠️ Please logout and login again for Docker permissions to take effect.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Installing...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed. Installing...${NC}"
    sudo apt update
    sudo apt install -y git
fi

echo -e "${BLUE}ℹ️ Checking system requirements...${NC}"

# Get production bot token from argument or prompt
if [ -z "$1" ]; then
    echo -e "${YELLOW}🔑 Please enter your PRODUCTION Telegram Bot Token:${NC}"
    echo -e "${YELLOW}   (Create a new bot via @BotFather - don't use your dev bot token)${NC}"
    read -s PROD_BOT_TOKEN
    echo
else
    PROD_BOT_TOKEN="$1"
fi

# Validate bot token format
if [[ ! $PROD_BOT_TOKEN =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
    echo -e "${RED}❌ Invalid bot token format. Should be like: 123456789:ABCdefGHI...${NC}"
    exit 1
fi

# Create project directory
PROJECT_DIR="$HOME/voice_memo_bot_prod"
echo -e "${BLUE}📁 Setting up project directory: $PROJECT_DIR${NC}"

if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️ Project directory exists. Updating...${NC}"
    cd "$PROJECT_DIR"
    git pull origin main
else
    echo -e "${BLUE}📥 Cloning repository...${NC}"
    git clone https://github.com/kdinof/voice_memo_to_txt_bot.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Create production .env file
echo -e "${BLUE}⚙️ Creating production environment file...${NC}"
cp .env.prod .env

# Update the bot token in .env file
sed -i "s/YOUR_PRODUCTION_BOT_TOKEN_HERE/$PROD_BOT_TOKEN/g" .env

echo -e "${GREEN}✅ Environment configured:${NC}"
echo -e "${GREEN}   - Same OpenAI API Key${NC}"
echo -e "${GREEN}   - Same Admin User (774945142)${NC}"
echo -e "${GREEN}   - New Production Bot Token${NC}"

# Stop existing containers if running
echo -e "${BLUE}🛑 Stopping any existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Build and start production containers
echo -e "${BLUE}🔨 Building and starting production containers...${NC}"
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for container to be healthy
echo -e "${BLUE}⏳ Waiting for bot to start...${NC}"
sleep 10

# Check if container is running
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${GREEN}🎉 SUCCESS! Bot is running in production mode.${NC}"
    echo
    echo -e "${GREEN}📊 Container Status:${NC}"
    docker-compose -f docker-compose.prod.yml ps
    echo
    echo -e "${BLUE}📋 Useful Commands:${NC}"
    echo "  View logs:    docker-compose -f docker-compose.prod.yml logs -f"
    echo "  Stop bot:     docker-compose -f docker-compose.prod.yml down"
    echo "  Restart bot:  docker-compose -f docker-compose.prod.yml restart"
    echo "  Update bot:   ./deploy.sh $PROD_BOT_TOKEN"
    echo
    echo -e "${BLUE}🔍 Database location:${NC}"
    echo "  Docker volume: bot_data_prod"
    echo "  Backup script: ./backup.sh"
    echo
    echo -e "${GREEN}✅ Your production bot is now running!${NC}"
    echo -e "${YELLOW}🔗 Find your bot on Telegram and test with /start${NC}"
else
    echo -e "${RED}❌ Failed to start bot. Checking logs...${NC}"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi