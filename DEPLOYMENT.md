# Production Deployment Guide

Deploy your Voice Memo Bot to any server with Docker support. This guide covers deployment to VPS, cloud servers, or dedicated servers.

## Prerequisites

- **Server**: Linux server (Ubuntu 20.04+ recommended)
- **Resources**: 1GB RAM minimum, 2GB recommended
- **Access**: SSH access with sudo privileges
- **New Bot**: Create a **new** Telegram bot for production (don't reuse development bot)

## Quick Deployment (Recommended)

### Step 1: Create Production Bot
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Choose name: "Your Bot Name PROD" 
4. Choose username: "your_bot_prod_bot"
5. **Save the bot token** - you'll need it for deployment

### Step 2: Server Setup
```bash
# Connect to your server
ssh your_user@your_server_ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for Docker permissions
exit
```

### Step 3: Automated Deployment
```bash
# Connect again after logout/login
ssh your_user@your_server_ip

# Download and run deployment script
curl -fsSL https://raw.githubusercontent.com/kdinof/voice_memo_to_txt_bot/main/deploy.sh -o deploy.sh
chmod +x deploy.sh

# Run deployment (will prompt for production bot token)
./deploy.sh

# Or pass token directly
./deploy.sh YOUR_PRODUCTION_BOT_TOKEN_HERE
```

**That's it!** Your bot should now be running in production.

---

## Manual Deployment

If you prefer manual setup:

### Step 1: Clone Repository
```bash
git clone https://github.com/kdinof/voice_memo_to_txt_bot.git
cd voice_memo_to_txt_bot
```

### Step 2: Configure Environment
```bash
# Copy production template
cp .env.prod .env

# Edit with your production bot token
nano .env
```

Replace `YOUR_PRODUCTION_BOT_TOKEN_HERE` with your actual production bot token.

### Step 3: Deploy with Docker
```bash
# Build and start production containers
docker-compose -f docker-compose.prod.yml up -d --build

# Check status
docker-compose -f docker-compose.prod.yml ps
```

---

## Configuration Details

### Environment Variables
Your production `.env` file will contain:

```env
# Same OpenAI API Key (reused from development)
OPENAI_API_KEY=sk-proj-...

# NEW production bot token (different from development)
TELEGRAM_BOT_TOKEN=YOUR_PRODUCTION_BOT_TOKEN

# Same admin user ID (your Telegram ID)
ADMIN_USER_ID=774945142

# Production database location
DATABASE_DIR=/home/app/data
NODE_ENV=production
```

### Key Differences from Development
- ✅ **Same Admin**: You keep admin access with same user ID
- ✅ **Same OpenAI**: Reuses your existing OpenAI API key  
- ✅ **New Bot**: Completely separate Telegram bot for production
- ✅ **Separate Database**: Production data isolated from development
- ✅ **Production Settings**: Optimized for production environment

---

## Management Commands

### Basic Operations
```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop bot
docker-compose -f docker-compose.prod.yml down

# Restart bot
docker-compose -f docker-compose.prod.yml restart

# Update to latest version
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

### Database Management
```bash
# Backup database
./backup.sh

# View database location
docker volume ls | grep bot_data_prod
```

### Monitoring
```bash
# Check container health
docker-compose -f docker-compose.prod.yml ps

# Monitor resource usage
docker stats voice-memo-bot-prod

# Check system resources
htop
df -h
```

---

## Testing Production Deployment

### 1. Basic Functionality Test
1. Find your production bot on Telegram
2. Send `/start` - should see welcome message with limits
3. Send `/usage` - should show 0 usage, 5 minutes remaining

### 2. Admin Commands Test
1. Send `/setpro 774945142 true` - should give you PRO status
2. Send `/start` again - should show "PRO User - Unlimited transcription!"
3. Send `/usage` - should show "Unlimited ✨"

### 3. Voice Processing Test
1. Send a short voice message
2. Should see 3 transcription options
3. Click any option to test transcription
4. Verify OpenAI API is working

---

## Security Best Practices

### Server Security
```bash
# Set up firewall
sudo ufw allow ssh
sudo ufw allow 22
sudo ufw enable

# Keep system updated
sudo apt update && sudo apt upgrade -y

# Monitor logs
tail -f /var/log/auth.log
```

### Application Security
- ✅ Bot runs as non-root user in container
- ✅ Read-only container filesystem
- ✅ Limited container resources
- ✅ Secrets via environment variables only
- ✅ Database in secure Docker volume

### Monitoring & Maintenance
```bash
# Set up log rotation
sudo nano /etc/logrotate.d/docker

# Add this content:
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  size 10M
  missingok
  delaycompress
  copytruncate
}
```

---

## Troubleshooting

### Common Issues

**Bot not responding:**
```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs
```

**Database issues:**
```bash
# Check database volume
docker volume inspect voice_memo_to_txt_bot_bot_data_prod

# Restart with clean database (⚠️ DELETES DATA)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

**Resource issues:**
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check Docker resources
docker system df
```

**API Issues:**
- Verify OpenAI API key is correct
- Check OpenAI account has credits
- Verify Telegram bot token is valid

### Log Analysis
```bash
# Search for errors
docker-compose -f docker-compose.prod.yml logs | grep -i error

# Search for specific user
docker-compose -f docker-compose.prod.yml logs | grep "774945142"

# Real-time monitoring
docker-compose -f docker-compose.prod.yml logs -f --tail=50
```

---

## Backup & Recovery

### Automated Backups
```bash
# Create backup script
nano backup-cron.sh
```

Add:
```bash
#!/bin/bash
cd /home/$(whoami)/voice_memo_to_txt_bot
./backup.sh
# Upload to cloud storage (optional)
# rsync backup_*.db user@backup-server:/backups/
```

```bash
# Make executable and add to cron
chmod +x backup-cron.sh
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/$(whoami)/voice_memo_to_txt_bot/backup-cron.sh
```

### Recovery
```bash
# Stop bot
docker-compose -f docker-compose.prod.yml down

# Replace database
docker run --rm -v voice_memo_to_txt_bot_bot_data_prod:/data -v $(pwd):/backup alpine cp /backup/backup_YYYYMMDD.db /data/bot_users.db

# Start bot
docker-compose -f docker-compose.prod.yml up -d
```

---

## Performance Optimization

### Resource Limits
The production configuration includes:
- **Memory Limit**: 512MB (can handle ~50 concurrent users)
- **CPU Limit**: 0.5 cores
- **Storage**: Unlimited (auto-grows with usage)

### Scaling Up
For high-traffic bots, consider:
- Increase memory limits in `docker-compose.prod.yml`
- Use dedicated database server (PostgreSQL)
- Add Redis for caching
- Implement rate limiting

Your production bot is now ready for real users! 🚀