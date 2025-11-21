"""
Auto-moderation module for OpenMod bot
Implements automatic moderation features
"""

import discord
from discord.ext import commands, tasks
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set

from utils.helpers import (
    is_mention_spam, 
    get_message_word_count, 
    is_valid_url, 
    is_valid_discord_invite,
    create_embed
)
from core.config import Config

class AutoModCog(commands.Cog, name="AutoMod"):
    """Auto-moderation commands and functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('openmod.automod')
        
        # Track message spam (user_id -> [message_times])
        self.message_spam_tracker: Dict[int, List[datetime]] = {}
        self.anti_invite_cache: Set[str] = set()  # Cache for invite codes
        
        # Start background tasks
        self.cleanup_spam_tracker.start()
        
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.cleanup_spam_tracker.cancel()
    
    @tasks.loop(minutes=5)
    async def cleanup_spam_tracker(self):
        """Clean up old entries from spam tracker"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(seconds=Config.SPAM_THRESHOLD_SECONDS + 10)
        
        for user_id in list(self.message_spam_tracker.keys()):
            # Filter out old timestamps
            self.message_spam_tracker[user_id] = [
                time for time in self.message_spam_tracker[user_id] 
                if time > cutoff_time
            ]
            
            # Remove user if no recent messages
            if not self.message_spam_tracker[user_id]:
                del self.message_spam_tracker[user_id]
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages to apply auto-moderation"""
        # Don't moderate bots or DMs
        if message.author.bot or not message.guild:
            return
            
        # Don't moderate admins/mods
        if message.author.guild_permissions.administrator or any(role.permissions.manage_guild for role in message.author.roles):
            return
        
        # Check for spam
        if await self.check_spam(message):
            return  # Message was handled as spam
            
        # Check for mention spam
        if await self.check_mention_spam(message):
            return  # Message was handled as mention spam
            
        # Check for invites
        if await self.check_invites(message):
            return  # Message was handled as invite spam
            
        # Check for word filtering
        if await self.check_word_filter(message):
            return  # Message was handled by word filter
    
    async def check_spam(self, message: discord.Message) -> bool:
        """Check if a message is part of spam"""
        user_id = message.author.id
        current_time = datetime.utcnow()
        
        # Add current message time to tracker
        if user_id not in self.message_spam_tracker:
            self.message_spam_tracker[user_id] = []
        
        self.message_spam_tracker[user_id].append(current_time)
        
        # Check if user has sent too many messages recently
        recent_messages = [
            time for time in self.message_spam_tracker[user_id]
            if (current_time - time).seconds <= Config.SPAM_THRESHOLD_SECONDS
        ]
        
        if len(recent_messages) > Config.SPAM_THRESHOLD_MESSAGES:
            # This is spam! Take action
            await self.handle_spam(message)
            return True
        
        return False
    
    async def check_mention_spam(self, message: discord.Message) -> bool:
        """Check if a message contains mention spam"""
        if is_mention_spam(message, Config.MENTION_SPAM_THRESHOLD):
            await self.handle_mention_spam(message)
            return True
        return False
    
    async def check_invites(self, message: discord.Message) -> bool:
        """Check if a message contains Discord invites"""
        # Look for invite patterns in the message
        if is_valid_discord_invite(message.content):
            # Get the invite code
            invite_code = get_invite_code(message.content)
            if invite_code and invite_code not in self.anti_invite_cache:
                # Check if this is a valid invite to this server
                try:
                    invite = await self.bot.fetch_invite(invite_code)
                    if invite.guild.id != message.guild.id:
                        # This is an invite to another server
                        await self.handle_invite(message)
                        return True
                except:
                    # If we can't fetch the invite, assume it's unwanted
                    await self.handle_invite(message)
                    return True
    
        return False
    
    async def check_word_filter(self, message: discord.Message) -> bool:
        """Check if a message contains filtered words"""
        # This would be implemented with a database of filtered words
        # For now, we'll just return False
        return False
    
    async def handle_spam(self, message: discord.Message):
        """Handle a spam message"""
        try:
            # Delete the spam message
            await message.delete()
            
            # Warn the user
            try:
                dm_embed = create_embed(
                    title="Spam Detected",
                    description=f"Your message in **{message.guild.name}** was deleted for spam",
                    color=discord.Color.red(),
                    fields=[
                        {"name": "Message", "value": message.content[:100] + "..." if len(message.content) > 100 else message.content, "inline": False},
                        {"name": "Action", "value": "Message deleted", "inline": True}
                    ]
                )
                await message.author.send(embed=dm_embed)
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
            # Log the incident
            guild_config = await self.bot.get_guild_config(message.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = message.guild.get_channel(mod_channel_id)
                if mod_channel:
                    embed = create_embed(
                        title="Spam Detected",
                        description=f"{message.author.mention} was detected for spam",
                        color=discord.Color.red(),
                        fields=[
                            {"name": "User", "value": f"{message.author} ({message.author.id})", "inline": True},
                            {"name": "Channel", "value": message.channel.mention, "inline": True},
                            {"name": "Message", "value": message.content[:100] + "..." if len(message.content) > 100 else message.content, "inline": False}
                        ]
                    )
                    await mod_channel.send(embed=embed)
            
            self.logger.info(f"Spam detected from {message.author} in {message.guild.name}")
        except discord.Forbidden:
            # We don't have permission to delete the message
            self.logger.warning(f"Could not delete spam message from {message.author} due to permission issues")
    
    async def handle_mention_spam(self, message: discord.Message):
        """Handle a mention spam message"""
        try:
            # Delete the mention spam message
            await message.delete()
            
            # Warn the user
            try:
                dm_embed = create_embed(
                    title="Mention Spam Detected",
                    description=f"Your message in **{message.guild.name}** was deleted for mention spam",
                    color=discord.Color.red(),
                    fields=[
                        {"name": "Message", "value": message.content[:100] + "..." if len(message.content) > 100 else message.content, "inline": False},
                        {"name": "Action", "value": "Message deleted", "inline": True}
                    ]
                )
                await message.author.send(embed=dm_embed)
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
            # Log the incident
            guild_config = await self.bot.get_guild_config(message.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = message.guild.get_channel(mod_channel_id)
                if mod_channel:
                    embed = create_embed(
                        title="Mention Spam Detected",
                        description=f"{message.author.mention} was detected for mention spam",
                        color=discord.Color.red(),
                        fields=[
                            {"name": "User", "value": f"{message.author} ({message.author.id})", "inline": True},
                            {"name": "Channel", "value": message.channel.mention, "inline": True},
                            {"name": "Mentions", "value": f"{len(message.mentions) + len(message.role_mentions)}", "inline": True},
                            {"name": "Message", "value": message.content[:100] + "..." if len(message.content) > 100 else message.content, "inline": False}
                        ]
                    )
                    await mod_channel.send(embed=embed)
            
            self.logger.info(f"Mention spam detected from {message.author} in {message.guild.name}")
        except discord.Forbidden:
            # We don't have permission to delete the message
            self.logger.warning(f"Could not delete mention spam message from {message.author} due to permission issues")
    
    async def handle_invite(self, message: discord.Message):
        """Handle a message containing an invite"""
        try:
            # Delete the invite message
            await message.delete()
            
            # Warn the user
            try:
                dm_embed = create_embed(
                    title="Invite Link Detected",
                    description=f"Your message in **{message.guild.name}** was deleted for containing an invite link",
                    color=discord.Color.red(),
                    fields=[
                        {"name": "Message", "value": message.content[:100] + "..." if len(message.content) > 100 else message.content, "inline": False},
                        {"name": "Action", "value": "Message deleted", "inline": True}
                    ]
                )
                await message.author.send(embed=dm_embed)
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
            # Log the incident
            guild_config = await self.bot.get_guild_config(message.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = message.guild.get_channel(mod_channel_id)
                if mod_channel:
                    embed = create_embed(
                        title="Invite Link Detected",
                        description=f"{message.author.mention} was detected for posting an invite link",
                        color=discord.Color.red(),
                        fields=[
                            {"name": "User", "value": f"{message.author} ({message.author.id})", "inline": True},
                            {"name": "Channel", "value": message.channel.mention, "inline": True},
                            {"name": "Message", "value": message.content[:100] + "..." if len(message.content) > 100 else message.content, "inline": False}
                        ]
                    )
                    await mod_channel.send(embed=embed)
            
            self.logger.info(f"Invite link detected from {message.author} in {message.guild.name}")
        except discord.Forbidden:
            # We don't have permission to delete the message
            self.logger.warning(f"Could not delete invite message from {message.author} due to permission issues")
    
    @commands.command(name='automod')
    @commands.has_permissions(manage_guild=True)
    async def automod_config(self, ctx: commands.Context, setting: str = None, value: str = None):
        """Configure auto-moderation settings"""
        if not setting:
            # Show current settings
            embed = create_embed(
                title="Auto-Moderation Settings",
                description="Current auto-mod settings for this server",
                color=discord.Color.blue(),
                fields=[
                    {"name": "Spam Threshold", "value": f"{Config.SPAM_THRESHOLD_MESSAGES} messages in {Config.SPAM_THRESHOLD_SECONDS} seconds", "inline": False},
                    {"name": "Mention Spam Threshold", "value": f"{Config.MENTION_SPAM_THRESHOLD} mentions", "inline": False},
                    {"name": "Auto-mod Enabled", "value": str(Config.ENABLE_AUTO_MOD), "inline": False}
                ]
            )
            await ctx.send(embed=embed)
            return
        
        # This would be expanded to actually update settings in a real implementation
        await ctx.send(f"Setting {setting} to {value} (configuration would be saved to database in full implementation)")


async def setup(bot):
    """Setup the auto-mod cog"""
    await bot.add_cog(AutoModCog(bot))