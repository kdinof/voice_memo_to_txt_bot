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
from database import init_database, can_process_voice, add_usage, get_user_stats, set_pro_status, get_all_users_stats, get_top_users_by_usage, get_daily_stats, get_user_details, export_usage_data

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
    user_id = update.effective_user.id
    is_pro, daily_usage, _ = get_user_stats(user_id)
    
    message = "👋 Hi! Send me a voice message and I'll convert it to text!\n\n"
    
    if is_pro:
        message += "✨ **PRO User** - Unlimited transcription!\n"
    else:
        remaining_seconds = max(0, 300 - daily_usage)
        remaining_minutes = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60
        message += f"📊 Daily limit: 5 minutes (you have {remaining_minutes}m {remaining_secs}s remaining today)\n"
    
    message += "\nCommands:\n/usage - Check your usage statistics\n"
    
    # Add admin commands info for admin users
    admin_id = os.getenv('ADMIN_USER_ID')
    if admin_id and str(user_id) == admin_id:
        message += "\n🔧 **Admin Commands:**\n"
        message += "/allusers - View all users statistics\n"
        message += "/topusers [limit] - Show top users by usage\n"
        message += "/userinfo <user_id> - Get detailed user info\n"
        message += "/dailystats - Today's usage statistics\n"
        message += "/export_usage - Export all usage data as CSV\n"
        message += "/setpro <user_id> <true/false> - Set PRO status\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

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
        
        # Check if user can process this voice message
        can_process, reason = can_process_voice(user_id, duration)
        if not can_process:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text=f"❌ {reason}"
            )
            return
        
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
        # Get user ID first
        user_id = query.from_user.id
        
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
        
        # Send final result as code block for easy copying
        await query.edit_message_text(f"```\n{result}\n```", parse_mode='Markdown')
        
        # Track usage after successful transcription
        add_usage(user_id, duration)
        
        logger.info(f"Successfully processed {transcription_type} transcription for cache_key: {cache_key}")
        logger.info(f"Added {duration} seconds of usage for user {user_id}")
        
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



async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's usage statistics."""
    user_id = update.effective_user.id
    is_pro, daily_usage, total_usage = get_user_stats(user_id)
    
    status = "PRO ✨" if is_pro else "Regular"
    daily_minutes = daily_usage // 60
    daily_seconds = daily_usage % 60
    total_minutes = total_usage // 60
    remaining_seconds = max(0, 300 - daily_usage) if not is_pro else float('inf')
    
    message = f"📊 **Your Usage Stats**\n\n"
    message += f"Status: {status}\n"
    message += f"Today: {daily_minutes}m {daily_seconds}s used\n"
    message += f"Total: {total_minutes}m used\n"
    
    if not is_pro:
        if remaining_seconds == float('inf'):
            message += f"Remaining: Unlimited"
        elif remaining_seconds > 0:
            rem_min = int(remaining_seconds) // 60
            rem_sec = int(remaining_seconds) % 60
            message += f"Remaining today: {rem_min}m {rem_sec}s"
        else:
            message += f"Daily limit reached (5 minutes)"
    else:
        message += f"Remaining: Unlimited ✨"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def setpro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set PRO status for users."""
    admin_id = os.getenv('ADMIN_USER_ID')
    if not admin_id or str(update.effective_user.id) != admin_id:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /setpro <user_id> <true/false>\n"
            "Example: /setpro 123456789 true"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        is_pro = context.args[1].lower() in ['true', '1', 'yes', 'on']
        
        success = set_pro_status(target_user_id, is_pro)
        if success:
            status = "PRO ✨" if is_pro else "Regular"
            await update.message.reply_text(f"✅ User {target_user_id} set to {status} status")
        else:
            await update.message.reply_text("❌ Failed to update user status")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Use numeric user ID.")
    except Exception as e:
        logger.error(f"Error in setpro command: {str(e)}")
        await update.message.reply_text("❌ Error updating user status")

async def allusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to show all users statistics."""
    admin_id = os.getenv('ADMIN_USER_ID')
    if not admin_id or str(update.effective_user.id) != admin_id:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        total_users, pro_users = get_all_users_stats()
        regular_users = total_users - pro_users
        
        message = f"👥 **All Users Statistics**\n\n"
        message += f"Total Users: {total_users}\n"
        message += f"PRO Users: {pro_users} ✨\n"
        message += f"Regular Users: {regular_users}\n"
        
        if total_users > 0:
            pro_percentage = (pro_users / total_users) * 100
            message += f"PRO Rate: {pro_percentage:.1f}%"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in allusers command: {str(e)}")
        await update.message.reply_text("❌ Error retrieving user statistics")

async def topusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to show top users by usage."""
    admin_id = os.getenv('ADMIN_USER_ID')
    if not admin_id or str(update.effective_user.id) != admin_id:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        limit = 10
        if context.args and context.args[0].isdigit():
            limit = min(int(context.args[0]), 50)  # Max 50 users
        
        top_users = get_top_users_by_usage(limit)
        
        if not top_users:
            await update.message.reply_text("📊 No users found")
            return
        
        message = f"📊 **Top {len(top_users)} Users by Usage**\n\n"
        
        for i, (user_id, total_seconds, is_pro) in enumerate(top_users, 1):
            total_minutes = total_seconds // 60
            remaining_seconds = total_seconds % 60
            status = "PRO ✨" if is_pro else "Regular"
            
            message += f"{i}. User {user_id} ({status})\n"
            message += f"   Usage: {total_minutes}m {remaining_seconds}s\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in topusers command: {str(e)}")
        await update.message.reply_text("❌ Error retrieving top users")

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to get detailed user information."""
    admin_id = os.getenv('ADMIN_USER_ID')
    if not admin_id or str(update.effective_user.id) != admin_id:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /userinfo <user_id>\n"
            "Example: /userinfo 123456789"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        user_details = get_user_details(target_user_id)
        
        if not user_details:
            await update.message.reply_text(f"❌ User {target_user_id} not found")
            return
        
        # Format user information
        status = "PRO ✨" if user_details['is_pro'] else "Regular"
        daily_minutes = user_details['daily_usage'] // 60
        daily_seconds = user_details['daily_usage'] % 60
        total_minutes = user_details['total_usage'] // 60
        
        message = f"👤 **User Information**\n\n"
        message += f"User ID: {user_details['user_id']}\n"
        message += f"Status: {status}\n"
        message += f"Joined: {user_details['created_at']}\n"
        message += f"Today's Usage: {daily_minutes}m {daily_seconds}s\n"
        message += f"Total Usage: {total_minutes}m\n\n"
        
        if user_details['usage_history']:
            message += "📅 **Recent Usage History:**\n"
            for date, seconds in user_details['usage_history']:
                minutes = seconds // 60
                remaining_secs = seconds % 60
                message += f"• {date}: {minutes}m {remaining_secs}s\n"
        else:
            message += "📅 No usage history found\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Use numeric user ID.")
    except Exception as e:
        logger.error(f"Error in userinfo command: {str(e)}")
        await update.message.reply_text("❌ Error retrieving user information")

async def dailystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to show daily statistics."""
    admin_id = os.getenv('ADMIN_USER_ID')
    if not admin_id or str(update.effective_user.id) != admin_id:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        active_users, total_seconds, total_transcriptions = get_daily_stats()
        total_minutes = total_seconds // 60
        remaining_seconds = total_seconds % 60
        
        message = f"📈 **Today's Statistics**\n\n"
        message += f"Active Users: {active_users}\n"
        message += f"Total Usage: {total_minutes}m {remaining_seconds}s\n"
        message += f"Transcriptions: {total_transcriptions}\n"
        
        if active_users > 0:
            avg_seconds_per_user = total_seconds // active_users
            avg_minutes = avg_seconds_per_user // 60
            avg_secs = avg_seconds_per_user % 60
            message += f"Avg per User: {avg_minutes}m {avg_secs}s"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in dailystats command: {str(e)}")
        await update.message.reply_text("❌ Error retrieving daily statistics")

async def export_usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to export usage data as CSV."""
    admin_id = os.getenv('ADMIN_USER_ID')
    if not admin_id or str(update.effective_user.id) != admin_id:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        await update.message.reply_text("📊 Generating usage data export...")
        
        csv_data = export_usage_data()
        
        if csv_data == "Error exporting data":
            await update.message.reply_text("❌ Error exporting usage data")
            return
        
        # Send CSV data as a code block for easy copying
        await update.message.reply_text(f"```csv\n{csv_data}\n```", parse_mode='Markdown')
        await update.message.reply_text("✅ Usage data exported successfully. Copy the CSV content above.")
        
    except Exception as e:
        logger.error(f"Error in export_usage command: {str(e)}")
        await update.message.reply_text("❌ Error exporting usage data")

def main() -> None:
    """Start the bot."""
    # Initialize database
    init_database()
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("usage", usage_command))
    application.add_handler(CommandHandler("setpro", setpro_command))
    application.add_handler(CommandHandler("allusers", allusers_command))
    application.add_handler(CommandHandler("topusers", topusers_command))
    application.add_handler(CommandHandler("userinfo", userinfo_command))
    application.add_handler(CommandHandler("dailystats", dailystats_command))
    application.add_handler(CommandHandler("export_usage", export_usage_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CallbackQueryHandler(handle_transcription_callback, pattern="^transcribe_"))

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 