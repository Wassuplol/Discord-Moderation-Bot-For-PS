"""
Moderation module for OpenMod bot
Implements core moderation commands and functionality
"""

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Union

from utils.helpers import (
    create_embed, 
    is_admin_or_mod, 
    has_permissions_for_action, 
    escape_markdown,
    format_timedelta
)
from core.config import Config

class ModerationCog(commands.Cog, name="Moderation"):
    """Moderation commands and functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('openmod.moderation')
        
    async def cog_check(self, ctx: commands.Context) -> bool:
        """Global check for all moderation commands"""
        # Only allow commands in guilds (not DMs)
        if not ctx.guild:
            return False
            
        # Check if user is admin/mod or has required permissions
        return is_admin_or_mod(ctx.author)
    
    @commands.command(name='warn')
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member for inappropriate behavior"""
        if member.bot:
            await ctx.send("You cannot warn a bot.")
            return
            
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You cannot warn someone with a higher or equal role.")
            return
        
        # Log the warning in the database
        success = await self.bot.db_manager.log_moderation_action(
            guild_id=ctx.guild.id,
            user_id=member.id,
            moderator_id=ctx.author.id,
            action_type='warn',
            reason=reason
        )
        
        if success:
            # Send DM to the warned user
            try:
                dm_embed = create_embed(
                    title="You have been warned",
                    description=f"You have received a warning in **{ctx.guild.name}**",
                    color=discord.Color.orange(),
                    fields=[
                        {"name": "Reason", "value": escape_markdown(reason), "inline": False},
                        {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                        {"name": "Date", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                    ]
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
            # Send confirmation to the channel
            embed = create_embed(
                title="Member Warned",
                description=f"{member.mention} has been warned",
                color=discord.Color.orange(),
                fields=[
                    {"name": "User", "value": f"{member} ({member.id})", "inline": True},
                    {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                    {"name": "Reason", "value": escape_markdown(reason), "inline": False}
                ]
            )
            await ctx.send(embed=embed)
            
            # Log to moderation channel if configured
            guild_config = await self.bot.get_guild_config(ctx.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = ctx.guild.get_channel(mod_channel_id)
                if mod_channel:
                    await mod_channel.send(embed=embed)
        else:
            await ctx.send("Failed to log warning. Please contact an administrator.")
    
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        if member.bot:
            await ctx.send("You cannot kick a bot.")
            return
            
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You cannot kick someone with a higher or equal role.")
            return
        
        # Log the kick in the database
        success = await self.bot.db_manager.log_moderation_action(
            guild_id=ctx.guild.id,
            user_id=member.id,
            moderator_id=ctx.author.id,
            action_type='kick',
            reason=reason
        )
        
        if success:
            try:
                # Send DM to the kicked user
                dm_embed = create_embed(
                    title="You have been kicked",
                    description=f"You have been kicked from **{ctx.guild.name}**",
                    color=discord.Color.red(),
                    fields=[
                        {"name": "Reason", "value": escape_markdown(reason), "inline": False},
                        {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                        {"name": "Date", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                    ]
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
            # Perform the kick
            await member.kick(reason=f"[{ctx.author}] {reason}")
            
            # Send confirmation to the channel
            embed = create_embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked from the server",
                color=discord.Color.red(),
                fields=[
                    {"name": "User", "value": f"{member} ({member.id})", "inline": True},
                    {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                    {"name": "Reason", "value": escape_markdown(reason), "inline": False}
                ]
            )
            await ctx.send(embed=embed)
            
            # Log to moderation channel if configured
            guild_config = await self.bot.get_guild_config(ctx.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = ctx.guild.get_channel(mod_channel_id)
                if mod_channel:
                    await mod_channel.send(embed=embed)
        else:
            await ctx.send("Failed to log kick. Please contact an administrator.")
    
    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: Union[discord.Member, int], *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        user_id = member if isinstance(member, int) else member.id
        member_obj = None
        
        if isinstance(member, discord.Member):
            member_obj = member
            
            if member.bot:
                await ctx.send("You cannot ban a bot.")
                return
                
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("You cannot ban someone with a higher or equal role.")
                return
        
        # Log the ban in the database
        success = await self.bot.db_manager.log_moderation_action(
            guild_id=ctx.guild.id,
            user_id=user_id,
            moderator_id=ctx.author.id,
            action_type='ban',
            reason=reason
        )
        
        if success:
            if member_obj:  # User is in the server
                try:
                    # Send DM to the banned user
                    dm_embed = create_embed(
                        title="You have been banned",
                        description=f"You have been banned from **{ctx.guild.name}**",
                        color=discord.Color.red(),
                        fields=[
                            {"name": "Reason", "value": escape_markdown(reason), "inline": False},
                            {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                            {"name": "Date", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                        ]
                    )
                    await member_obj.send(embed=dm_embed)
                except discord.Forbidden:
                    # User has DMs disabled
                    pass
                
                # Perform the ban
                await member_obj.ban(reason=f"[{ctx.author}] {reason}", delete_message_days=0)
            else:  # User is not in the server, try to ban by ID
                try:
                    user = await self.bot.fetch_user(user_id)
                    await ctx.guild.ban(user, reason=f"[{ctx.author}] {reason}", delete_message_days=0)
                except discord.NotFound:
                    await ctx.send("User not found.")
                    return
                except discord.Forbidden:
                    await ctx.send("I don't have permission to ban this user.")
                    return
            
            # Send confirmation to the channel
            user_display = f"<@{user_id}>" if not member_obj else member_obj.mention
            user_name = f"(ID: {user_id})" if not member_obj else f"{member_obj} ({member_obj.id})"
            
            embed = create_embed(
                title="Member Banned",
                description=f"{user_display} has been banned from the server",
                color=discord.Color.red(),
                fields=[
                    {"name": "User", "value": user_name, "inline": True},
                    {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                    {"name": "Reason", "value": escape_markdown(reason), "inline": False}
                ]
            )
            await ctx.send(embed=embed)
            
            # Log to moderation channel if configured
            guild_config = await self.bot.get_guild_config(ctx.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = ctx.guild.get_channel(mod_channel_id)
                if mod_channel:
                    await mod_channel.send(embed=embed)
        else:
            await ctx.send("Failed to log ban. Please contact an administrator.")
    
    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = "No reason provided"):
        """Unban a user by ID"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"[{ctx.author}] {reason}")
            
            # Update moderation log to mark ban as inactive (unbanned)
            # This would require a method to update moderation actions in the DB
            
            embed = create_embed(
                title="User Unbanned",
                description=f"{user.mention} has been unbanned",
                color=discord.Color.green(),
                fields=[
                    {"name": "User", "value": f"{user} ({user.id})", "inline": True},
                    {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                    {"name": "Reason", "value": escape_markdown(reason), "inline": False}
                ]
            )
            await ctx.send(embed=embed)
            
            # Log to moderation channel if configured
            guild_config = await self.bot.get_guild_config(ctx.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = ctx.guild.get_channel(mod_channel_id)
                if mod_channel:
                    await mod_channel.send(embed=embed)
        except discord.NotFound:
            await ctx.send("User not found or not banned.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban this user.")
    
    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str = "30m", *, reason: str = "No reason provided"):
        """Mute a member for a specified duration"""
        if member.bot:
            await ctx.send("You cannot mute a bot.")
            return
            
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You cannot mute someone with a higher or equal role.")
            return
        
        # Parse duration
        try:
            duration_seconds = self.parse_duration(duration)
            if duration_seconds <= 0:
                await ctx.send("Invalid duration format. Use: 10s, 5m, 2h, 1d, etc.")
                return
        except ValueError:
            await ctx.send("Invalid duration format. Use: 10s, 5m, 2h, 1d, etc.")
            return
        
        # Find or create a mute role
        mute_role = None
        for role in ctx.guild.roles:
            if "mute" in role.name.lower() or "muted" in role.name.lower():
                mute_role = role
                break
        
        if not mute_role:
            # Create a new mute role if one doesn't exist
            try:
                mute_role = await ctx.guild.create_role(
                    name="Muted",
                    reason="Mute role for OpenMod moderation system"
                )
                
                # Set permissions for the mute role in all channels
                for channel in ctx.guild.channels:
                    try:
                        await channel.set_permissions(
                            mute_role,
                            send_messages=False,
                            add_reactions=False,
                            speak=False,
                            connect=False
                        )
                    except:
                        continue  # Skip channels where we can't set permissions
            except discord.Forbidden:
                await ctx.send("I don't have permission to create a mute role.")
                return
        
        # Add the mute role to the member
        try:
            await member.add_roles(mute_role, reason=f"[{ctx.author}] {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to mute this member.")
            return
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        # Log the mute in the database
        success = await self.bot.db_manager.log_moderation_action(
            guild_id=ctx.guild.id,
            user_id=member.id,
            moderator_id=ctx.author.id,
            action_type='mute',
            reason=reason,
            expires_at=expires_at
        )
        
        if success:
            # Send DM to the muted user
            try:
                dm_embed = create_embed(
                    title="You have been muted",
                    description=f"You have been muted in **{ctx.guild.name}**",
                    color=discord.Color.orange(),
                    fields=[
                        {"name": "Duration", "value": duration, "inline": True},
                        {"name": "Reason", "value": escape_markdown(reason), "inline": False},
                        {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                        {"name": "Expires", "value": expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                    ]
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
            # Send confirmation to the channel
            embed = create_embed(
                title="Member Muted",
                description=f"{member.mention} has been muted",
                color=discord.Color.orange(),
                fields=[
                    {"name": "User", "value": f"{member} ({member.id})", "inline": True},
                    {"name": "Duration", "value": duration, "inline": True},
                    {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                    {"name": "Reason", "value": escape_markdown(reason), "inline": False},
                    {"name": "Expires", "value": expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": False}
                ]
            )
            await ctx.send(embed=embed)
            
            # Log to moderation channel if configured
            guild_config = await self.bot.get_guild_config(ctx.guild.id)
            mod_channel_id = guild_config.get('moderation_channel_id')
            if mod_channel_id:
                mod_channel = ctx.guild.get_channel(mod_channel_id)
                if mod_channel:
                    await mod_channel.send(embed=embed)
            
            # Schedule unmute task
            await self.schedule_unmute(member.id, ctx.guild.id, duration_seconds)
        else:
            await ctx.send("Failed to log mute. Please contact an administrator.")
    
    @commands.command(name='purge', aliases=['clear'])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, limit: int = 10, user: discord.User = None):
        """Purge messages from a channel"""
        if limit <= 0 or limit > 100:
            await ctx.send("Please specify a number between 1 and 100.")
            return
        
        try:
            if user:
                def is_user(message):
                    return message.author.id == user.id
                
                deleted = await ctx.channel.purge(limit=limit + 1, check=is_user)
            else:
                deleted = await ctx.channel.purge(limit=limit + 1)  # +1 to include the command message
            
            # Send confirmation
            confirmation = await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=3)
        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages.")
    
    @commands.command(name='slowmode')
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, duration: str = "0s"):
        """Set slowmode for the current channel"""
        try:
            seconds = self.parse_duration(duration)
            
            if seconds < 0 or seconds > 21600:  # Max 6 hours
                await ctx.send("Slowmode duration must be between 0 seconds and 6 hours.")
                return
            
            await ctx.channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                await ctx.send("Slowmode has been disabled for this channel.")
            else:
                embed = create_embed(
                    title="Slowmode Updated",
                    description=f"Slowmode set to {duration} for this channel.",
                    color=discord.Color.blue(),
                    fields=[
                        {"name": "Channel", "value": ctx.channel.mention, "inline": True},
                        {"name": "Moderator", "value": ctx.author.mention, "inline": True},
                        {"name": "Duration", "value": duration, "inline": True}
                    ]
                )
                await ctx.send(embed=embed)
        except ValueError:
            await ctx.send("Invalid duration format. Use: 10s, 5m, 2h, 1d, etc.")
    
    def parse_duration(self, duration_str: str) -> int:
        """Parse a duration string like '30s', '5m', '2h', '1d' into seconds"""
        if duration_str == "0s":
            return 0
            
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        # Extract number and unit
        num_str = ''.join(filter(str.isdigit, duration_str))
        unit_str = ''.join(filter(str.isalpha, duration_str)).lower()
        
        if not num_str or not unit_str or unit_str not in units:
            raise ValueError("Invalid duration format")
        
        num = int(num_str)
        unit = units[unit_str]
        
        return num * unit
    
    async def schedule_unmute(self, user_id: int, guild_id: int, duration_seconds: int):
        """Schedule an unmute task"""
        await asyncio.sleep(duration_seconds)
        
        # Get the guild and member
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
            
        member = guild.get_member(user_id)
        if not member:
            return
        
        # Find the mute role
        mute_role = None
        for role in guild.roles:
            if "mute" in role.name.lower() or "muted" in role.name.lower():
                mute_role = role
                break
        
        if mute_role and mute_role in member.roles:
            try:
                await member.remove_roles(mute_role, reason="Temporary mute expired")
                
                # Send DM to the user
                try:
                    dm_embed = create_embed(
                        title="You have been unmuted",
                        description=f"Your mute in **{guild.name}** has expired",
                        color=discord.Color.green()
                    )
                    await member.send(embed=dm_embed)
                except discord.Forbidden:
                    # User has DMs disabled
                    pass
            except discord.Forbidden:
                # Don't have permission to remove role
                pass

async def setup(bot):
    """Setup the moderation cog"""
    await bot.add_cog(ModerationCog(bot))