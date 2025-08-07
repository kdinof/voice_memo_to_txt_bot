import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Use absolute path for Docker volume mounting, fallback to current directory for local dev
DATABASE_DIR = os.getenv('DATABASE_DIR', '.')
DATABASE_FILE = os.path.join(DATABASE_DIR, 'bot_users.db')

def init_database() -> None:
    """Initialize the database with required tables."""
    try:
        # Ensure database directory exists
        os.makedirs(DATABASE_DIR, exist_ok=True)
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_pro INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create usage_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                seconds_used INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_or_create_user(user_id: int) -> bool:
    """Get user from database or create if doesn't exist. Returns True if user is PRO."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Try to get existing user
        cursor.execute('SELECT is_pro FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            is_pro = bool(result[0])
        else:
            # Create new user
            cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            is_pro = False
            logger.info(f"Created new user {user_id}")
        
        conn.close()
        return is_pro
        
    except Exception as e:
        logger.error(f"Error getting/creating user {user_id}: {str(e)}")
        return False

def get_daily_usage(user_id: int) -> int:
    """Get total seconds used by user today."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        cursor.execute(
            'SELECT seconds_used FROM usage_logs WHERE user_id = ? AND date = ?',
            (user_id, today)
        )
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 0
        
    except Exception as e:
        logger.error(f"Error getting daily usage for user {user_id}: {str(e)}")
        return 0

def add_usage(user_id: int, seconds: int) -> None:
    """Add usage seconds for user today."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        # Try to update existing record
        cursor.execute('''
            UPDATE usage_logs 
            SET seconds_used = seconds_used + ? 
            WHERE user_id = ? AND date = ?
        ''', (seconds, user_id, today))
        
        # If no record was updated, create new one
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO usage_logs (user_id, date, seconds_used) 
                VALUES (?, ?, ?)
            ''', (user_id, today, seconds))
        
        conn.commit()
        conn.close()
        logger.info(f"Added {seconds} seconds of usage for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error adding usage for user {user_id}: {str(e)}")

def set_pro_status(user_id: int, is_pro: bool) -> bool:
    """Set PRO status for user. Returns True if successful."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Ensure user exists first
        get_or_create_user(user_id)
        
        # Update PRO status
        cursor.execute(
            'UPDATE users SET is_pro = ? WHERE user_id = ?',
            (1 if is_pro else 0, user_id)
        )
        
        conn.commit()
        conn.close()
        
        status = "PRO" if is_pro else "regular"
        logger.info(f"Set user {user_id} to {status} status")
        return True
        
    except Exception as e:
        logger.error(f"Error setting PRO status for user {user_id}: {str(e)}")
        return False

def get_user_stats(user_id: int) -> Tuple[bool, int, int]:
    """Get user statistics: (is_pro, daily_usage_seconds, total_usage_seconds)."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Get PRO status and daily usage
        is_pro = get_or_create_user(user_id)
        daily_usage = get_daily_usage(user_id)
        
        # Get total usage across all days
        cursor.execute(
            'SELECT SUM(seconds_used) FROM usage_logs WHERE user_id = ?',
            (user_id,)
        )
        result = cursor.fetchone()
        total_usage = result[0] if result and result[0] else 0
        
        conn.close()
        return is_pro, daily_usage, total_usage
        
    except Exception as e:
        logger.error(f"Error getting stats for user {user_id}: {str(e)}")
        return False, 0, 0

def can_process_voice(user_id: int, duration_seconds: int) -> Tuple[bool, str]:
    """Check if user can process voice message. Returns (can_process, reason)."""
    is_pro, daily_usage, _ = get_user_stats(user_id)
    
    # PRO users have unlimited access
    if is_pro:
        return True, "PRO user - unlimited access"
    
    # Check daily limit (5 minutes = 300 seconds)
    DAILY_LIMIT = 300
    remaining_seconds = DAILY_LIMIT - daily_usage
    
    if duration_seconds > remaining_seconds:
        if remaining_seconds <= 0:
            return False, "Daily limit exceeded (5 minutes). Upgrade to PRO for unlimited access."
        else:
            remaining_minutes = remaining_seconds // 60
            remaining_secs = remaining_seconds % 60
            return False, f"Voice message too long. You have {remaining_minutes}m {remaining_secs}s remaining today."
    
    return True, f"Processing allowed. {remaining_seconds - duration_seconds}s remaining today."