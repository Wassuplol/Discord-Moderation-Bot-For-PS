"""
Core bot class for OpenMod
Handles bot initialization, event handling, and module loading
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

import discord
from discord.ext import commands
from discord.ext.commands import when_mentioned_or

from core.config import Config
from utils.helpers import get_cog_list
from core.version import __version__

class OpenModBot(commands.Bot):
    """
    Main bot class for OpenMod
    Extends discord.ext.commands.Bot with additional functionality
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Database manager (will be set after initialization)
        self.db_manager = None
        
        # Statistics and performance tracking
        self.stats = {
            'commands_executed': 0,
            'messages_processed': 0,
            'start_time': None
        }
        
        # Cache for performance
        self.guild_configs = {}
        self.user_cache = {}
        
        # Logging
        self.logger = logging.getLogger('openmod.bot')
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        self.logger.info("OpenMod Bot is starting up...")
        self.stats['start_time'] = discord.utils.utcnow()
        
        # Load all cogs automatically
        await self.load_all_cogs()
        
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        self.logger.info(f'{self.user} has connected to Discord!')
        self.logger.info(f'Guilds: {len(self.guilds)}')
        self.logger.info(f'Users: {len(self.users)}')
        self.logger.info(f'Shards: {self.shard_count}')
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"your server | v{__version__} | 100% Free & Open Source"
            )
        )
        
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from bots (including this bot)
        if message.author.bot:
            return
            
        # Update message counter
        self.stats['messages_processed'] += 1
        
        # Process commands
        await self.process_commands(message)
        
    async def on_command(self, ctx: commands.Context):
        """Called when a command is executed"""
        self.stats['commands_executed'] += 1
        
        # Log command execution
        self.logger.info(
            f"Command '{ctx.command}' executed by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}"
        )
        
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found. Use `/help` for a list of commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don't have the required permissions to execute this command.")
        else:
            self.logger.error(f"Error in command {ctx.command}: {error}")
            await ctx.send("An error occurred while executing the command.")
            
    async def load_all_cogs(self):
        """Load all cogs from the modules directory"""
        modules_dir = Path(__file__).parent.parent / "modules"
        
        # Find all Python files in modules directory
        cog_files = list(modules_dir.rglob("*.py"))
        
        loaded_cogs = []
        failed_cogs = []
        
        for cog_file in cog_files:
            # Skip __init__.py files
            if cog_file.name == "__init__.py":
                continue
                
            # Convert file path to module path
            relative_path = cog_file.relative_to(Path(__file__).parent.parent)
            module_path = str(relative_path).replace(os.sep, '.')[:-3]  # Remove .py extension
            
            try:
                await self.load_extension(module_path)
                loaded_cogs.append(module_path)
                self.logger.info(f"Loaded cog: {module_path}")
            except Exception as e:
                failed_cogs.append((module_path, str(e)))
                self.logger.error(f"Failed to load cog {module_path}: {e}")
                
        self.logger.info(f"Successfully loaded {len(loaded_cogs)} cogs: {loaded_cogs}")
        if failed_cogs:
            self.logger.warning(f"Failed to load {len(failed_cogs)} cogs: {[c[0] for c in failed_cogs]}")
            
    async def close(self):
        """Clean up when the bot is shutting down"""
        self.logger.info("OpenMod Bot is shutting down...")
        
        # Close database connections
        if self.db_manager:
            await self.db_manager.close()
            
        await super().close()
        
    def get_uptime(self) -> str:
        """Get the bot's uptime as a formatted string"""
        if not self.stats['start_time']:
            return "Not started yet"
            
        uptime = discord.utils.utcnow() - self.stats['start_time']
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        
        return f"{days}d {hours}h {minutes}m {seconds}s"
        
    async def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Get guild-specific configuration"""
        if guild_id not in self.guild_configs:
            # In a real implementation, this would fetch from the database
            self.guild_configs[guild_id] = {
                'prefix': Config.BOT_PREFIX,
                'moderation_channels': [],
                'auto_mod_settings': {},
                'custom_commands': {},
            }
            
        return self.guild_configs[guild_id]