"""
Helper functions for OpenMod bot
Contains common utility functions used throughout the application
"""

import re
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import discord
from discord.ext import commands

def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL"""
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url) is not None

def is_valid_discord_invite(invite: str) -> bool:
    """Check if a string is a valid Discord invite"""
    # Match various Discord invite formats
    patterns = [
        r'discord\.gg/([a-zA-Z0-9-]+)',
        r'discord\.com/invite/([a-zA-Z0-9-]+)',
        r'discordapp\.com/invite/([a-zA-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, invite)
        if match:
            return True
    return False

def get_invite_code(invite: str) -> Optional[str]:
    """Extract invite code from Discord invite URL"""
    patterns = [
        r'discord\.gg/([a-zA-Z0-9-]+)',
        r'discord\.com/invite/([a-zA-Z0-9-]+)',
        r'discordapp\.com/invite/([a-zA-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, invite)
        if match:
            return match.group(1)
    return None

def is_mention_spam(message: discord.Message, threshold: int = 10) -> bool:
    """Check if a message contains excessive mentions"""
    mention_count = len(message.mentions) + len(message.role_mentions)
    return mention_count >= threshold

def get_message_word_count(message: discord.Message) -> int:
    """Get the number of words in a message"""
    # Remove mentions and URLs from the content for more accurate word count
    content = re.sub(r'<@!?[0-9]+>|<#[0-9]+>|<@&[0-9]+>|https?://[^\s]+', '', message.content)
    return len(content.split())

def sanitize_text(text: str) -> str:
    """Sanitize text by removing potentially harmful content"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove potentially harmful content (customize as needed)
    return text.strip()

def format_timedelta(td: timedelta) -> str:
    """Format a timedelta object into a human-readable string"""
    seconds = int(td.total_seconds())
    periods = [
        ('year', 60*60*24*365),
        ('month', 60*60*24*30),
        ('day', 60*60*24),
        ('hour', 60*60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append(f"{period_value} {period_name}{has_s}")

    return ", ".join(strings)

def format_datetime(dt: datetime) -> str:
    """Format a datetime object into a human-readable string"""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def get_member_display_name(member: discord.Member) -> str:
    """Get a member's display name"""
    return member.display_name or member.name

def escape_markdown(text: str) -> str:
    """Escape markdown characters in text"""
    markdown_chars = ['_', '*', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '[', ']']
    for char in markdown_chars:
        text = text.replace(char, f'\\{char}')
    return text

def create_embed(title: str = "", description: str = "", color: discord.Color = discord.Color.blue(), 
                fields: List[Dict[str, str]] = None, footer: str = "", timestamp: bool = True) -> discord.Embed:
    """Create a formatted embed"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow() if timestamp else None
    )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', ''),
                value=field.get('value', ''),
                inline=field.get('inline', True)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    return embed

def has_permissions_for_action(ctx: commands.Context, required_permissions: List[str]) -> bool:
    """Check if the user has the required permissions for an action"""
    if ctx.guild is None:  # DM context
        return ctx.author.id == ctx.bot.owner_id
    
    # Check if user is bot owner
    if ctx.author.id == ctx.bot.owner_id:
        return True
    
    # Check if user has administrator permission
    if ctx.author.guild_permissions.administrator:
        return True
    
    # Check specific permissions
    author_permissions = ctx.channel.permissions_for(ctx.author)
    for perm in required_permissions:
        if not getattr(author_permissions, perm, False):
            return False
    
    return True

def is_admin_or_mod(member: discord.Member) -> bool:
    """Check if a member is an admin or moderator"""
    # Check for administrator permission
    if member.guild_permissions.administrator:
        return True
    
    # Check for moderator-like permissions
    mod_permissions = [
        'manage_guild',
        'manage_channels',
        'kick_members',
        'ban_members',
        'manage_messages',
        'manage_roles'
    ]
    
    member_permissions = member.guild_permissions
    for perm in mod_permissions:
        if getattr(member_permissions, perm, False):
            return True
    
    # Check for roles with "mod", "admin", or "staff" in the name
    for role in member.roles:
        role_name = role.name.lower()
        if any(keyword in role_name for keyword in ['mod', 'admin', 'staff']):
            return True
    
    return False


def is_admin():
    """Decorator to check if the command invoker is an admin"""
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:  # DM context
            return ctx.author.id == ctx.bot.owner_id
        
        # Check if user is bot owner
        if ctx.author.id == ctx.bot.owner_id:
            return True
        
        # Check if user has administrator permission
        if ctx.author.guild_permissions.administrator:
            return True
        
        # Check for moderator-like permissions
        mod_permissions = [
            'manage_guild',
            'manage_channels',
            'kick_members',
            'ban_members',
            'manage_messages',
            'manage_roles'
        ]
        
        author_permissions = ctx.channel.permissions_for(ctx.author)
        for perm in mod_permissions:
            if getattr(author_permissions, perm, False):
                return True
        
        # Check for roles with "mod", "admin", or "staff" in the name
        for role in ctx.author.roles:
            role_name = role.name.lower()
            if any(keyword in role_name for keyword in ['mod', 'admin', 'staff']):
                return True
        
        return False
    
    return commands.check(predicate)

async def safe_delete_message(message: discord.Message, delay: float = 0.0):
    """Safely delete a message with error handling"""
    try:
        if delay > 0:
            await asyncio.sleep(delay)
        await message.delete()
    except discord.NotFound:
        # Message was already deleted
        pass
    except discord.Forbidden:
        # Bot doesn't have permission to delete the message
        pass
    except discord.HTTPException:
        # Some other error occurred
        pass

def get_cog_list() -> List[str]:
    """Get a list of available cogs (this would be implemented based on your module structure)"""
    # This is a placeholder - in a real implementation, this would scan the modules directory
    return [
        'moderation',
        'utility', 
        'logging',
        'automod',
        'leveling',
        'tickets',
        'giveaways',
        'suggestions',
        'polls',
        'ticket',  # v2.0 addition
        'reaction_roles',  # v2.0 addition
        'auto_responder',  # v2.0 addition
        'custom_commands',  # v2.0 addition
        'verification'  # v2.0 addition
    ]

def validate_user_input(text: str, max_length: int = 1000, allowed_chars: str = None) -> bool:
    """Validate user input for safety and length"""
    if len(text) > max_length:
        return False
    
    if allowed_chars:
        # Check if all characters in text are in allowed_chars
        return all(c in allowed_chars for c in text)
    
    # Basic validation - check for potentially harmful patterns
    harmful_patterns = [
        r'<script.*?>',  # HTML script tags
        r'javascript:',   # JavaScript URLs
        r'on\w+\s*=',    # Event handlers
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    
    return True

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def get_ordinal_suffix(number: int) -> str:
    """Get the ordinal suffix for a number (st, nd, rd, th)"""
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return str(number) + suffix