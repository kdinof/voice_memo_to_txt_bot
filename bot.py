import os
import logging
import tempfile
import traceback
import hashlib
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import OpenAI, OpenAIError
import ffmpeg
import json
import asyncio
from prompts import BASIC_PROMPT, SUMMARY_PROMPT, TRANSLATE_PROMPT, SYSTEM_PROMPTS, MODEL_CONFIG

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary to store voice file data temporarily
voice_files_cache = {}

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
    """Handle incoming voice messages by showing transcription options."""
    processing_msg = None
    try:
        # Send initial processing message
        processing_msg = await update.message.reply_text("🎤 Processing your voice message...")
        
        # Get voice message details
        voice = update.message.voice
        file_id = voice.file_id
        duration = voice.duration
        user_id = update.effective_user.id
        
        logger.info(f"Received voice message. File ID: {file_id}, Duration: {duration}s, User: {user_id}")
        
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
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="🎤 Converting audio format..."
            )
            logger.info("Converting audio from OGG to MP3")
            await convert_audio(temp_path, temp_converted_path)
            logger.info("Audio conversion successful")
        except Exception as e:
            logger.error(f"Error converting audio: {str(e)}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="❌ Error converting audio. Please try again."
            )
            return
        
        # Store voice file data for callback processing (use shorter key for callback data limit)
        cache_key = hashlib.md5(f"{user_id}_{file_id}".encode()).hexdigest()[:16]
        voice_files_cache[cache_key] = {
            'temp_converted_path': temp_converted_path,
            'temp_path': temp_path,
            'duration': duration,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Create inline keyboard with transcription options
        keyboard = [
            [InlineKeyboardButton("📝 Basic Transcription", callback_data=f"transcribe_basic_{cache_key}")],
            [InlineKeyboardButton("📋 Summarize Long Text", callback_data=f"transcribe_summary_{cache_key}")],
            [InlineKeyboardButton("🌐 Translate to English", callback_data=f"transcribe_translate_{cache_key}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message with transcription options
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text="🎤 Audio processed! Choose your transcription type:",
            reply_markup=reply_markup
        )
        
        logger.info(f"Voice file cached and options presented to user {user_id}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if processing_msg:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="❌ Sorry, something went wrong. Please try again later."
            )
        else:
            await update.message.reply_text("❌ Sorry, something went wrong. Please try again later.")
        
        # Clean up temporary files on error
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
            if 'temp_converted_path' in locals():
                os.unlink(temp_converted_path)
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up temporary files: {str(cleanup_error)}")


async def process_transcription(transcription_type: str, temp_converted_path: str, duration: int) -> str:
    """Process transcription based on the selected type."""
    try:
        # Transcribe using OpenAI Whisper
        logger.info("Starting transcription with OpenAI Whisper")
        with open(temp_converted_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        logger.info("Transcription completed successfully")
        
        # Select prompt and model based on transcription type
        prompt_templates = {
            "basic": BASIC_PROMPT,
            "summary": SUMMARY_PROMPT,
            "translate": TRANSLATE_PROMPT
        }
        
        if transcription_type not in prompt_templates:
            raise ValueError(f"Unknown transcription type: {transcription_type}")
            
        prompt = prompt_templates[transcription_type].format(transcription=transcription)
        model = MODEL_CONFIG[transcription_type]
        system_content = SYSTEM_PROMPTS[transcription_type]
        
        # Process with GPT
        logger.info(f"Starting text processing with {model}")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
        )
        
        processed_text = completion.choices[0].message.content
        logger.info(f"Text processing completed successfully with {model}")
        
        return processed_text
        
    except Exception as e:
        logger.error(f"Error in transcription processing: {str(e)}")
        # Return raw transcription as fallback
        if 'transcription' in locals():
            return f"📝 Raw transcription (processing failed):\n\n{transcription}"
        else:
            raise

async def handle_transcription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from transcription type buttons."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Parse callback data
        callback_data = query.data
        parts = callback_data.split('_', 2)
        if len(parts) != 3 or parts[0] != "transcribe":
            raise ValueError("Invalid callback data format")
        
        transcription_type = parts[1]  # basic, summary, or translate
        cache_key = parts[2]
        
        # Get cached voice file data
        if cache_key not in voice_files_cache:
            await query.edit_message_text("❌ Voice message expired. Please send a new voice message.")
            return
        
        voice_data = voice_files_cache[cache_key]
        temp_converted_path = voice_data['temp_converted_path']
        temp_path = voice_data['temp_path']
        duration = voice_data['duration']
        
        # Check file exists
        if not os.path.exists(temp_converted_path):
            await query.edit_message_text("❌ Voice file not found. Please send a new voice message.")
            voice_files_cache.pop(cache_key, None)
            return
        
        # Update message to show processing
        type_labels = {
            "basic": "📝 Basic Transcription",
            "summary": "📋 Summarization", 
            "translate": "🌐 Translation"
        }
        await query.edit_message_text(f"🎤 Processing {type_labels.get(transcription_type, 'transcription')}...")
        
        # Process transcription
        result = await process_transcription(transcription_type, temp_converted_path, duration)
        
        # Send final result
        emoji_map = {"basic": "📝", "summary": "📋", "translate": "🌐"}
        emoji = emoji_map.get(transcription_type, "✅")
        await query.edit_message_text(f"{emoji} Here's your result:\n\n{result}")
        
        logger.info(f"Successfully processed {transcription_type} transcription for cache_key: {cache_key}")
        
    except Exception as e:
        logger.error(f"Error in callback handler: {str(e)}")
        await query.edit_message_text("❌ Error processing your request. Please try again.")
    
    finally:
        # Clean up cached files
        if 'cache_key' in locals() and cache_key in voice_files_cache:
            voice_data = voice_files_cache[cache_key]
            try:
                if os.path.exists(voice_data['temp_path']):
                    os.unlink(voice_data['temp_path'])
                if os.path.exists(voice_data['temp_converted_path']):
                    os.unlink(voice_data['temp_converted_path'])
                voice_files_cache.pop(cache_key, None)
                logger.info(f"Cleaned up files for cache_key: {cache_key}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up cached files: {str(cleanup_error)}")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CallbackQueryHandler(handle_transcription_callback, pattern="^transcribe_"))

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 