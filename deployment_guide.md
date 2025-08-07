# DigitalOcean VPS Deployment Guide

## Prerequisites
- DigitalOcean VPS with Ubuntu 22.04 LTS
- SSH access to your server
- Your server IP address
- OpenAI API key
- Telegram bot token

## Step 1: Connect to Your VPS

```bash
ssh root@YOUR_SERVER_IP
```

## Step 2: Update System and Install Dependencies

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git ffmpeg curl

# Install Node.js and PM2 for process management
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

## Step 3: Create Non-Root User (Recommended)

```bash
# Create new user
adduser botuser
usermod -aG sudo botuser

# Switch to new user
su - botuser
```

## Step 4: Clone Repository

```bash
# Clone your repository
git clone https://github.com/kdinof/voice_memo_to_txt_bot.git
cd voice_memo_to_txt_bot
```

## Step 5: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 6: Configure Environment Variables

```bash
# Create .env file
nano .env
```

Add your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

## Step 7: Test the Bot

```bash
# Test run (should show "Starting bot..." message)
python bot.py
```

Press `Ctrl+C` to stop after confirming it works.

## Step 8: Set Up PM2 Process Manager

```bash
# Create PM2 ecosystem file
nano ecosystem.config.js
```

Add this configuration:
```javascript
module.exports = {
  apps: [{
    name: 'voice-bot',
    script: 'bot.py',
    interpreter: './venv/bin/python',
    cwd: '/home/botuser/voice_memo_to_txt_bot',
    env: {
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true
  }]
}
```

```bash
# Create logs directory
mkdir logs

# Start bot with PM2
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Set up PM2 to start on boot
pm2 startup
# Follow the command it gives you (run with sudo)
```

## Step 9: Set Up Systemd Service (Alternative to PM2)

If you prefer systemd over PM2:

```bash
sudo nano /etc/systemd/system/voice-bot.service
```

Add:
```ini
[Unit]
Description=Voice Message Transcription Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/voice_memo_to_txt_bot
Environment=PATH=/home/botuser/voice_memo_to_txt_bot/venv/bin
ExecStart=/home/botuser/voice_memo_to_txt_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable voice-bot
sudo systemctl start voice-bot

# Check status
sudo systemctl status voice-bot
```

## Step 10: Set Up Firewall (Optional but Recommended)

```bash
# Set up basic firewall
sudo ufw allow ssh
sudo ufw allow 22
sudo ufw enable
```

## Step 11: Monitor Your Bot

### Using PM2:
```bash
# View logs
pm2 logs voice-bot

# Monitor processes
pm2 monit

# Restart bot
pm2 restart voice-bot
```

### Using systemd:
```bash
# View logs
sudo journalctl -u voice-bot -f

# Restart service
sudo systemctl restart voice-bot
```

## Step 12: Set Up Auto-Updates (Optional)

```bash
# Create update script
nano update_bot.sh
```

Add:
```bash
#!/bin/bash
cd /home/botuser/voice_memo_to_txt_bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pm2 restart voice-bot
echo "Bot updated successfully!"
```

```bash
# Make executable
chmod +x update_bot.sh
```

## Troubleshooting

### Check if bot is running:
```bash
pm2 status
# or
sudo systemctl status voice-bot
```

### View logs:
```bash
pm2 logs voice-bot
# or
sudo journalctl -u voice-bot -f
```

### Common issues:
1. **FFmpeg not found**: Make sure ffmpeg is installed: `sudo apt install ffmpeg`
2. **Permission errors**: Check file ownership: `sudo chown -R botuser:botuser /home/botuser/voice_memo_to_txt_bot`
3. **API key errors**: Verify .env file exists and has correct keys

## Security Recommendations

1. **Use non-root user**: Always run the bot as a non-root user
2. **Keep system updated**: Regularly run `sudo apt update && sudo apt upgrade`
3. **Monitor logs**: Regularly check logs for errors or suspicious activity
4. **Backup configuration**: Keep backups of your .env file and configuration

Your bot should now be running 24/7 on your DigitalOcean VPS!