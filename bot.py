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
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key not found in environment variables")
logger.info(f"OpenAI API Key found and loaded")

try:
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Hello! I'm your voice-to-text bot. Just send me a voice message and I'll transcribe and structure it for you!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🤖 How to use this bot:\n\n"
        "1. Send me a voice message in English or Russian\n"
        "2. I'll transcribe it using OpenAI's Whisper\n"
        "3. I'll structure the text using GPT\n"
        "4. You'll receive the structured text back\n\n"
        "That's it! Just send me a voice message to get started."
    )

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages."""
    temp_path = None
    temp_converted_path = None
    processing_msg = None
    
    try:
        # Send a processing message
        processing_msg = await update.message.reply_text("🎤 Processing your voice message...")
        
        # Get the voice message file
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        logger.info(f"Received voice message. File ID: {voice.file_id}, Duration: {voice.duration}s")
        
        # Create temporary files for the voice message
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file, \
             tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_converted_file:
            temp_path = temp_file.name
            temp_converted_path = temp_converted_file.name
            logger.info(f"Created temporary files at: {temp_path} and {temp_converted_path}")
        
        try:
            # Download the file
            await file.download_to_drive(temp_path)
            file_size = os.path.getsize(temp_path)
            logger.info(f"Voice message downloaded to {temp_path} (Size: {file_size} bytes)")
            
            if not os.path.exists(temp_path):
                raise FileNotFoundError(f"Downloaded file not found at {temp_path}")
            
            if file_size == 0:
                raise ValueError("Downloaded file is empty")
            
            # Convert OGG to MP3 (Whisper works better with MP3)
            try:
                logger.info("Converting audio from OGG to MP3")
                await convert_audio(temp_path, temp_converted_path)
                logger.info("Audio conversion successful")
            except Exception as e:
                logger.error(f"Error converting audio: {str(e)}")
                logger.error(f"ffmpeg stdout: {e.stdout.decode('utf8')}")
                logger.error(f"ffmpeg stderr: {e.stderr.decode('utf8')}")
                raise
            
            # Update status
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="🎤 Transcribing your voice message..."
            )
            
            # Transcribe the audio using Whisper
            try:
                logger.info("Starting transcription with Whisper API")
                with open(temp_converted_path, "rb") as audio_file:
                    logger.debug("File opened successfully for transcription")
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    
                if not transcript:
                    raise ValueError("Transcription returned empty result")
                    
                logger.info(f"Transcription successful. Text: {transcript}")
                
            except OpenAIError as e:
                logger.error(f"OpenAI API Error during transcription: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"API Response: {e.response}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during transcription: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            # Update status
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="🤖 Structuring the text..."
            )
            
            # Structure the text using GPT
            try:
                logger.info("Starting GPT text structuring")
                structure_prompt = f""" Reformat the user message.
 - Use a format appropriate for texting, or instant messaging.
 - Fix grammar, spelling, and punctuation.
 - Remove speech artifacts (um, uh, false starts, repetitions).
 - Maintain original tone.
 - Correct homophones, standardize numbers and dates.
 - Add paragraphs or lists as needed.
 - Never precede output with any intro like “Here is the corrected text:”.
 - Don’t add content not in the source or answer questions in it.
 - Don’t add sign-offs or acknowledgments that aren’t in the source.
 - NEVER answer questions that are presented in the text. Only reply with the corrected text.
 - If there is text that is a question, you are not requested to be an AI Assistant and find the answer.  
 - You are ONLY asked to correct text, spelling, format, etc as mentioned above. 
 - You should never output the answer to a question.
 - If there is NO text provided, do not return anything in the output.
                
                Text to structure:
                {transcript}"""
                
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that structures text in a clear and organized way."},
                        {"role": "user", "content": structure_prompt}
                    ]
                )
                
                if not completion.choices:
                    raise ValueError("GPT response contained no choices")
                    
                structured_text = completion.choices[0].message.content
                logger.info("Text structuring successful")
                logger.debug(f"Structured text: {structured_text[:100]}...")
                
            except OpenAIError as e:
                logger.error(f"OpenAI API Error during text structuring: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"API Response: {e.response}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during text structuring: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            # Send the final result
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text=f"✅ Here's your structured text:\n\n{structured_text}",
                parse_mode='Markdown'
            )
            
        finally:
            # Clean up the temporary files
            for path in [temp_path, temp_converted_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                        logger.info(f"Temporary file {path} cleaned up")
                    except Exception as e:
                        logger.error(f"Error cleaning up temporary file: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error processing voice message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        error_message = f"❌ Sorry, something went wrong: {str(e)}"
        
        if processing_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id,
                    text=error_message[:4000]  # Telegram message limit
                )
            except Exception as e2:
                logger.error(f"Error updating error message: {str(e2)}")
                await update.message.reply_text("❌ Sorry, something went wrong. Please try again later.")
        else:
            await update.message.reply_text("❌ Sorry, something went wrong. Please try again later.")

async def convert_audio(input_path: str, output_path: str) -> None:
    """Convert audio file from OGG to MP3 using ffmpeg directly with pipes."""
    try:
        # Use ffmpeg directly with pipes for better performance
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

def main():
    """Start the bot."""
    try:
        # Create the Application and pass it your bot's token
        application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        
        # Add voice message handler
        application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

        # Start the Bot
        logger.info("Starting bot...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Critical error starting bot: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == '__main__':
    main() 