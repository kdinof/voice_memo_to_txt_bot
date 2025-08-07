# Voice-to-Text Telegram Bot

A Telegram bot that converts voice messages to text using OpenAI's Whisper API with daily usage limits and PRO user support.

## Features

- 🎤 Converts voice messages to text using OpenAI Whisper
- 🤖 Multiple transcription types: Basic, Summarization, Translation  
- ⏱️ Daily usage limits (5 minutes for regular users)
- ✨ PRO user system with unlimited access
- 📊 Usage tracking and statistics
- 🐳 Docker support for easy deployment
- 🔧 Admin commands for user management
- 🎛️ Real-time progress updates during processing

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+ with FFmpeg (for manual setup)
- OpenAI API key  
- Telegram Bot Token

## Quick Start (Docker - Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/voice-to-text-bot.git
cd voice-to-text-bot
```

2. Create a `.env` file with your API keys:
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Required environment variables:
```env
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ADMIN_USER_ID=your_telegram_user_id  # For PRO user management
```

3. Start with Docker Compose:
```bash
# Development mode (with live code reload)
docker-compose up --build

# Production mode 
docker-compose -f docker-compose.prod.yml up -d --build
```

4. Send a voice message to your bot on Telegram!

## Manual Installation (Alternative)

<details>
<summary>Click to expand manual setup instructions</summary>

1. Clone and enter directory:
```bash
git clone https://github.com/yourusername/voice-to-text-bot.git
cd voice-to-text-bot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian  
sudo apt-get install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

5. Set up environment and run:
```bash
cp .env.example .env
# Edit .env with your API keys
python bot.py
```

</details>

## Usage & Commands

### For Users
- Send any voice message to get transcription options
- `/start` - Welcome message with usage info
- `/usage` - Check your daily usage statistics

### Transcription Types
- **📝 Basic Transcription** - Clean up and format text
- **📋 Summarization** - Intelligent summarization for long content  
- **🌐 Translation** - Translate to English with formatting

### For Admins
- `/setpro <user_id> <true/false>` - Grant or revoke PRO status
- Set `ADMIN_USER_ID` in `.env` to use admin commands

## User Limits

- **Regular Users**: 5 minutes of transcription per day
- **PRO Users**: Unlimited transcription ✨
- Limits reset daily at midnight UTC

## Docker Commands

```bash
# Development
docker-compose up --build                    # Start in foreground
docker-compose up -d --build                # Start in background  
docker-compose logs -f                      # View logs
docker-compose down                         # Stop containers

# Production  
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml down

# Database backup (production)
docker-compose -f docker-compose.prod.yml exec voice-memo-bot cp /home/app/data/bot_users.db /tmp/
docker cp voice-memo-bot-prod:/tmp/bot_users.db ./backup_$(date +%Y%m%d).db
```

## Architecture

### Core Components
- **bot.py**: Main application with bot logic and handlers
- **database.py**: User management and usage tracking with SQLite
- **prompts.py**: AI prompt templates for different transcription types
- **Docker**: Multi-stage build with Python 3.11 + FFmpeg

### Audio Processing Pipeline
1. Voice message received → temporary OGG file
2. FFmpeg converts OGG to MP3 format  
3. User chooses transcription type via inline buttons
4. OpenAI Whisper transcribes audio
5. GPT models process text based on selected type
6. Structured result sent to user, usage tracked

## Deployment Options

### Docker (Recommended)
- ✅ Consistent environment with FFmpeg pre-installed
- ✅ Database persistence via Docker volumes
- ✅ Production-ready with health checks and resource limits
- ✅ Easy deployment to any Docker-compatible platform

### Traditional Hosting
- Works on Render, Heroku, VPS, etc.
- Requires manual FFmpeg installation
- Database persistence depends on platform

## Monitoring

- Health checks via SQLite database connectivity
- Structured logging with rotation
- Resource limits in production configuration
- Usage statistics and tracking per user

## License

MIT License

## Contributing

Feel free to submit issues and enhancement requests! 