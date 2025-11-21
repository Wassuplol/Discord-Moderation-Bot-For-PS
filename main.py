"""
OpenMod - The Completely Free, Open-Source Discord Moderation Bot
MIT License - 2023 OpenMod
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from core.bot import OpenModBot
from core.config import Config
from core.database import DatabaseManager
from core.logger import setup_logging

# Load environment variables
load_dotenv()

# Set up logging
setup_logging()

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True  # Required for moderation features
intents.members = True
intents.presences = True
intents.voice_states = True
intents.bans = True
intents.emojis_and_stickers = True
intents.integrations = True
intents.webhooks = True
intents.invites = True
intents.reactions = True
intents.typing = False  # We don't need typing events
intents.guild_scheduled_events = True

# Bot instance
bot = OpenModBot(
    command_prefix=Config.BOT_PREFIX,
    intents=intents,
    case_insensitive=True,
    help_command=None,  # We'll implement a custom help system
    owner_id=Config.BOT_OWNER_ID,
    description="OpenMod - The Completely Free, Open-Source Discord Moderation Bot"
)

async def main():
    """Main entry point for the bot."""
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.init()
        
        # Store database manager in bot instance
        bot.db_manager = db_manager
        
        # Load all cogs (modules)
        await bot.load_all_cogs()
        
        # Start the bot
        await bot.start(Config.BOT_TOKEN)
        
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt received. Shutting down...")
        await bot.close()
    except Exception as e:
        logging.error(f"An error occurred while running the bot: {e}")
        await bot.close()
    finally:
        print("Bot has been shut down.")

if __name__ == "__main__":
    asyncio.run(main())