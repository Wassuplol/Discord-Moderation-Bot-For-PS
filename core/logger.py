"""
Logging module for OpenMod bot
Sets up logging configuration for the entire application
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from core.config import Config

def setup_logging():
    """Set up logging configuration for the bot"""
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('openmod')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join(logs_dir, Config.LOG_FILE)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Set discord.py logging level
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    # Set our bot module logging level
    bot_logger = logging.getLogger('openmod.bot')
    bot_logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f'openmod.{name}')

# Initialize the main logger when this module is imported
main_logger = setup_logging()