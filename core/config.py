"""
Configuration module for OpenMod bot
Handles all configuration settings and environment variables
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class containing all bot settings"""
    
    # Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
    BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', 0)) if os.getenv('BOT_OWNER_ID') else None
    BOT_DESCRIPTION = os.getenv('BOT_DESCRIPTION', 'OpenMod - The Completely Free, Open-Source Discord Moderation Bot')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///openmod.db')
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')  # 'sqlite' or 'postgresql'
    
    # Redis Configuration (optional, for caching)
    REDIS_URL = os.getenv('REDIS_URL', '')
    REDIS_ENABLED = bool(REDIS_URL)
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'openmod.log')
    
    # Moderation Configuration
    MODERATION_LOG_CHANNEL = os.getenv('MODERATION_LOG_CHANNEL', 'mod-logs')
    MESSAGE_LOG_CHANNEL = os.getenv('MESSAGE_LOG_CHANNEL', 'message-logs')
    MEMBER_LOG_CHANNEL = os.getenv('MEMBER_LOG_CHANNEL', 'member-logs')
    
    # Auto-mod Configuration
    SPAM_THRESHOLD_MESSAGES = int(os.getenv('SPAM_THRESHOLD_MESSAGES', 5))
    SPAM_THRESHOLD_SECONDS = int(os.getenv('SPAM_THRESHOLD_SECONDS', 10))
    MENTION_SPAM_THRESHOLD = int(os.getenv('MENTION_SPAM_THRESHOLD', 10))
    
    # Data Retention Settings
    MESSAGE_LOG_RETENTION_DAYS = int(os.getenv('MESSAGE_LOG_RETENTION_DAYS', 7))
    MODERATION_LOG_RETENTION_DAYS = int(os.getenv('MODERATION_LOG_RETENTION_DAYS', 180))
    USER_DATA_RETENTION_DAYS = int(os.getenv('USER_DATA_RETENTION_DAYS', 180))
    
    # Performance Settings
    MAX_CACHE_SIZE = int(os.getenv('MAX_CACHE_SIZE', 10000))
    BACKGROUND_TASK_DELAY = float(os.getenv('BACKGROUND_TASK_DELAY', 1.0))
    
    # Web Dashboard Configuration
    WEB_DASHBOARD_ENABLED = os.getenv('WEB_DASHBOARD_ENABLED', 'false').lower() == 'true'
    WEB_HOST = os.getenv('WEB_HOST', '127.0.0.1')
    WEB_PORT = int(os.getenv('WEB_PORT', 5000))
    WEB_SECRET_KEY = os.getenv('WEB_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Rate Limiting
    GLOBAL_RATE_LIMIT = int(os.getenv('GLOBAL_RATE_LIMIT', 3))  # Commands per minute per user
    CHANNEL_RATE_LIMIT = int(os.getenv('CHANNEL_RATE_LIMIT', 5))  # Messages per minute per channel
    
    # Privacy Settings
    COLLECT_USAGE_STATS = os.getenv('COLLECT_USAGE_STATS', 'false').lower() == 'true'
    ANONYMIZE_USER_DATA = os.getenv('ANONYMIZE_USER_DATA', 'true').lower() == 'true'
    
    # Feature Toggles
    ENABLE_AUTO_MOD = os.getenv('ENABLE_AUTO_MOD', 'true').lower() == 'true'
    ENABLE_LEVELING = os.getenv('ENABLE_LEVELING', 'true').lower() == 'true'
    ENABLE_TICKETS = os.getenv('ENABLE_TICKETS', 'true').lower() == 'true'
    ENABLE_GIVEAWAYS = os.getenv('ENABLE_GIVEAWAYS', 'true').lower() == 'true'
    ENABLE_SUGGESTIONS = os.getenv('ENABLE_SUGGESTIONS', 'true').lower() == 'true'
    ENABLE_POLLS = os.getenv('ENABLE_POLLS', 'true').lower() == 'true'
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if not cls.BOT_TOKEN:
            issues.append("BOT_TOKEN is not set")
        
        if not cls.BOT_OWNER_ID:
            issues.append("BOT_OWNER_ID is not set")
        
        if cls.DATABASE_TYPE not in ['sqlite', 'postgresql']:
            issues.append(f"Invalid DATABASE_TYPE: {cls.DATABASE_TYPE}. Must be 'sqlite' or 'postgresql'")
        
        return issues
    
    @classmethod
    def get_database_config(cls) -> dict:
        """Get database configuration as a dictionary"""
        return {
            'url': cls.DATABASE_URL,
            'type': cls.DATABASE_TYPE,
            'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', 30)),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 3600)),
        }