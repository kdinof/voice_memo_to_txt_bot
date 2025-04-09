# Voice-to-Text Telegram Bot

A Telegram bot that converts voice messages to text using OpenAI's Whisper API.

## Features

- Converts voice messages to text
- Uses OpenAI's Whisper API for accurate transcription
- Handles various audio formats (OGG, MP3)
- Asynchronous processing for better performance

## Prerequisites

- Python 3.13 or higher
- FFmpeg
- OpenAI API key
- Telegram Bot Token

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/voice-to-text-bot.git
cd voice-to-text-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
```bash
# On macOS
brew install ffmpeg

# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On Windows
# Download from https://ffmpeg.org/download.html
```

5. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Send a voice message to your bot on Telegram
3. The bot will convert the voice message to text and send it back to you

## Configuration

You can modify the following settings in `bot.py`:
- Audio conversion parameters
- OpenAI model settings
- Logging configuration

## License

MIT License

## Contributing

Feel free to submit issues and enhancement requests! 