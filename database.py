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

def get_all_users_stats() -> Tuple[int, int]:
    """Get overall user statistics: (total_users, pro_users)."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Get total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Get PRO users
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_pro = 1')
        pro_users = cursor.fetchone()[0]
        
        conn.close()
        return total_users, pro_users
        
    except Exception as e:
        logger.error(f"Error getting all users stats: {str(e)}")
        return 0, 0

def get_top_users_by_usage(limit: int = 10) -> list:
    """Get top users by total usage. Returns list of (user_id, total_seconds, is_pro)."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, COALESCE(SUM(ul.seconds_used), 0) as total_usage, u.is_pro
            FROM users u
            LEFT JOIN usage_logs ul ON u.user_id = ul.user_id
            GROUP BY u.user_id, u.is_pro
            ORDER BY total_usage DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error getting top users: {str(e)}")
        return []

def get_daily_stats() -> Tuple[int, int, int]:
    """Get daily statistics: (active_users_today, total_seconds_today, total_transcriptions_today)."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        # Get active users today
        cursor.execute('SELECT COUNT(*) FROM usage_logs WHERE date = ?', (today,))
        active_users = cursor.fetchone()[0]
        
        # Get total seconds used today
        cursor.execute('SELECT COALESCE(SUM(seconds_used), 0) FROM usage_logs WHERE date = ?', (today,))
        total_seconds = cursor.fetchone()[0]
        
        # Get total transcriptions (count of usage log entries) today
        cursor.execute('SELECT COUNT(*) FROM usage_logs WHERE date = ? AND seconds_used > 0', (today,))
        total_transcriptions = cursor.fetchone()[0]
        
        conn.close()
        return active_users, total_seconds, total_transcriptions
        
    except Exception as e:
        logger.error(f"Error getting daily stats: {str(e)}")
        return 0, 0, 0

def get_user_details(user_id: int) -> Optional[dict]:
    """Get detailed user information including join date and usage history."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Get user basic info
        cursor.execute('SELECT is_pro, created_at FROM users WHERE user_id = ?', (user_id,))
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return None
        
        is_pro, created_at = user_result
        
        # Get usage stats
        is_pro_bool, daily_usage, total_usage = get_user_stats(user_id)
        
        # Get usage history (last 7 days)
        cursor.execute('''
            SELECT date, seconds_used 
            FROM usage_logs 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT 7
        ''', (user_id,))
        usage_history = cursor.fetchall()
        
        conn.close()
        
        return {
            'user_id': user_id,
            'is_pro': bool(is_pro),
            'created_at': created_at,
            'daily_usage': daily_usage,
            'total_usage': total_usage,
            'usage_history': usage_history
        }
        
    except Exception as e:
        logger.error(f"Error getting user details for {user_id}: {str(e)}")
        return None

def export_usage_data() -> str:
    """Export all usage data as CSV string."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.is_pro, u.created_at,
                   COALESCE(ul.date, 'N/A') as usage_date,
                   COALESCE(ul.seconds_used, 0) as seconds_used
            FROM users u
            LEFT JOIN usage_logs ul ON u.user_id = ul.user_id
            ORDER BY u.user_id, ul.date DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        # Create CSV string
        csv_lines = ['user_id,is_pro,created_at,usage_date,seconds_used']
        for row in results:
            csv_lines.append(','.join(str(item) for item in row))
        
        return '\n'.join(csv_lines)
        
    except Exception as e:
        logger.error(f"Error exporting usage data: {str(e)}")
        return "Error exporting data"