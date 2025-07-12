# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot that transcribes voice messages using OpenAI's Whisper API and then structures the transcribed text using GPT-3.5-turbo. The bot supports multiple languages (English/Russian) and provides real-time progress updates during processing.

## Architecture

### Core Components
- **bot.py**: Main application containing bot logic and handlers
- **prompts.py**: Prompt templates and model configurations for transcription types
- **Voice Processing Pipeline**: Download → Convert (OGG to MP3) → Show Options → Transcribe → Structure → Send
- **External Dependencies**: Telegram Bot API, OpenAI Whisper API, OpenAI Chat Completions API, FFmpeg

### Key Functions
- `handle_voice()` (bot.py:69): Main voice message processing pipeline with progress updates
- `convert_audio()` (bot.py:34): Asynchronous audio format conversion using ffmpeg subprocess
- `start()` (bot.py:65): Bot initialization and welcome message handler

### Audio Processing Flow
1. Voice message received → temporary OGG file created
2. FFmpeg converts OGG to MP3 format asynchronously
3. User shown inline buttons with 3 transcription options
4. MP3 file sent to OpenAI Whisper for transcription
5. Raw transcription processed with selected GPT model and prompt
6. Structured text returned to user, temporary files cleaned up

### Transcription Types
- **Basic Transcription**: GPT-4o-mini for fast text cleaning and formatting
- **Summarization**: GPT-4o for intelligent summarization of long content
- **Translation**: GPT-4o-mini for English translation with text cleaning

## Environment Setup

### Required Environment Variables
```
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### System Dependencies
- Python 3.13+
- FFmpeg (required for audio conversion)

### Installation Commands
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg
```

## Development Commands

### Running the Bot
```bash
python bot.py
```

### Testing
No formal test suite is currently implemented. Test manually by:
1. Starting the bot locally
2. Sending voice messages via Telegram
3. Monitoring console logs for errors

## Deployment

### Production Environment
- Configured for Render deployment (see Procfile)
- Uses worker process: `python bot.py`
- Requires environment variables to be set in hosting platform

### Key Deployment Files
- **Procfile**: Defines worker process for Render/Heroku
- **requirements.txt**: Python dependencies
- **.env.example**: Template for environment variables
- **.gitignore**: Excludes sensitive files and build artifacts

## Error Handling

The bot includes comprehensive error handling with user-friendly messages:
- Audio conversion failures
- OpenAI API errors (transcription and structuring)
- Telegram API communication issues
- Automatic temporary file cleanup in all error scenarios

## Logging

Uses Python's built-in logging module with INFO level. Key events logged:
- Voice message receipt and processing stages
- Audio conversion success/failure
- API call results
- File cleanup operations