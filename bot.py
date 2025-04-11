import os
import logging
import tempfile
import traceback
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI, OpenAIError
import ffmpeg
import json
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
try:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OpenAI API key not found in environment variables")
    client = OpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    raise

async def convert_audio(input_path: str, output_path: str) -> None:
    """Convert audio file from OGG to MP3 using ffmpeg directly."""
    try:
        # Use ffmpeg directly for better performance
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_path,  # Input file
            '-f', 'mp3',      # Output format
            '-acodec', 'libmp3lame',  # Audio codec
            '-ab', '192k',    # Bitrate
            '-ar', '44100',   # Sample rate
            '-y',            # Overwrite output file if exists
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"FFmpeg conversion failed: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('👋 Hi! Send me a voice message and I\'ll convert it to text!')

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages."""
    try:
        # Get voice message details
        voice = update.message.voice
        file_id = voice.file_id
        duration = voice.duration
        
        logger.info(f"Received voice message. File ID: {file_id}, Duration: {duration}s")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg, \
             tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
            temp_path = temp_ogg.name
            temp_converted_path = temp_mp3.name
            
        logger.info(f"Created temporary files at: {temp_path} and {temp_converted_path}")
        
        # Download the voice message
        voice_file = await context.bot.get_file(file_id)
        await voice_file.download_to_drive(temp_path)
        logger.info(f"Voice message downloaded to {temp_path} (Size: {os.path.getsize(temp_path)} bytes)")
        
        # Convert OGG to MP3
        try:
            logger.info("Converting audio from OGG to MP3")
            await convert_audio(temp_path, temp_converted_path)
            logger.info("Audio conversion successful")
        except Exception as e:
            logger.error(f"Error converting audio: {str(e)}")
            await update.message.reply_text("❌ Error converting audio. Please try again.")
            return
        
        # Transcribe using OpenAI
        try:
            logger.info("Starting transcription with OpenAI")
            with open(temp_converted_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            logger.info("Transcription completed successfully")
            
            # Structure the text using GPT
            try:
                logger.info("Starting text structuring with GPT")
                structure_prompt = f"""Reformat the following text:
- Use a format appropriate for texting or instant messaging
- Fix grammar, spelling, and punctuation
- Remove speech artifacts (um, uh, false starts, repetitions)
- Maintain original tone
- Correct homophones, standardize numbers and dates
- Add paragraphs or lists as needed
- Never precede output with any intro like "Here is the corrected text:"
- Don't add content not in the source or answer questions in it
- Don't add sign-offs or acknowledgments that aren't in the source
- NEVER answer questions that are presented in the text. Only reply with the corrected text.

Text to structure:
{transcription}"""

                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that structures text in a clear and organized way."},
                        {"role": "user", "content": structure_prompt}
                    ]
                )
                
                structured_text = completion.choices[0].message.content
                logger.info("Text structuring completed successfully")
                
                # Send the structured text back
                await update.message.reply_text(f"📝 Here's what you said:\n\n{structured_text}")
                
            except Exception as e:
                logger.error(f"Error in text structuring: {str(e)}")
                # If structuring fails, send the raw transcription
                await update.message.reply_text(f"📝 Here's the transcription:\n\n{transcription}")
            
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            await update.message.reply_text("❌ Error transcribing audio. Please try again.")
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await update.message.reply_text("❌ Sorry, something went wrong. Please try again later.")
        
    finally:
        # Clean up temporary files
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
            if 'temp_converted_path' in locals():
                os.unlink(temp_converted_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 