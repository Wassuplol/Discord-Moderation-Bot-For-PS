"""
Stream Notifications Module for OpenMod Discord Bot
Handles YouTube, Twitch, and Kick streaming notifications
"""
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
from datetime import datetime
import re
from typing import Dict, List, Optional

from core.database import StreamNotification
from utils.helpers import is_admin


class StreamNotifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_streams.start()
        # Cache to store last check times and stream status to reduce API calls
        self.stream_cache = {}
        
    def cog_unload(self):
        self.check_streams.cancel()

    @tasks.loop(minutes=5)  # Check every 5 minutes
    async def check_streams(self):
        """Background task to check for new streams/videos"""
        try:
            # Get the database manager from the bot
            db_manager = self.bot.db_manager
            
            # Get all registered streamers from database
            async with db_manager.async_session() as session:
                from sqlalchemy.future import select
                result = await session.execute(select(StreamNotification).filter_by(enabled=True))
                streamers = result.scalars().all()
            
            for streamer in streamers:
                if streamer.platform == 'youtube':
                    await self.check_youtube_stream(streamer)
                elif streamer.platform == 'twitch':
                    await self.check_twitch_stream(streamer)
                elif streamer.platform == 'kick':
                    await self.check_kick_stream(streamer)
                    
        except Exception as e:
            print(f"Error in stream checking task: {e}")

    async def check_youtube_stream(self, streamer: StreamNotification):
        """Check if a YouTube channel has uploaded a new video or is live streaming"""
        try:
            # For now, we'll implement a basic check using YouTube RSS feeds
            # In a real implementation, you would use the YouTube Data API
            # Format: https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
            # Or: https://www.youtube.com/feeds/videos.xml?user=USERNAME
            
            # Check if this is a channel ID or username
            if streamer.channel_id.startswith('UC') or streamer.channel_id.startswith('HC'):
                # This is a channel ID
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={streamer.channel_id}"
            else:
                # Assume it's a username
                rss_url = f"https://www.youtube.com/feeds/videos.xml?user={streamer.channel_id}"
            
            # Fetch the RSS feed
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Parse the RSS feed to get the latest video
                        from xml.etree import ElementTree as ET
                        root = ET.fromstring(content)
                        
                        # Find the first entry (most recent video)
                        entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                        if entries:
                            latest_entry = entries[0]
                            
                            # Extract video details
                            video_id = latest_entry.find('.//{http://www.youtube.com/xml/schemas/2015}videoId').text
                            title = latest_entry.find('.//{http://www.w3.org/2005/Atom}title').text
                            published = latest_entry.find('.//{http://www.w3.org/2005/Atom}published').text
                            
                            # Check if this is a new video (not the last one we saw)
                            if streamer.last_video_id != video_id:
                                # Update the database with the new video ID
                                await self.update_streamer_last_video_id(streamer.id, video_id)
                                
                                # Send notification
                                await self.send_youtube_notification(streamer, title, video_id)
                                
                    else:
                        print(f"Failed to fetch YouTube RSS for {streamer.channel_id}: {response.status}")
            
        except Exception as e:
            print(f"Error checking YouTube stream for {streamer.channel_id}: {e}")

    async def check_twitch_stream(self, streamer: StreamNotification):
        """Check if a Twitch channel is streaming"""
        try:
            # Note: In a real implementation, you would need to:
            # 1. Register a Twitch application to get Client ID and Client Secret
            # 2. Implement OAuth to get an access token
            # 3. Use the Twitch Helix API to check stream status
            
            # For now, we'll implement a basic version that would work with the API
            # This is a placeholder that would need actual API integration
            
            # In a real implementation:
            # 1. Get OAuth token from config
            # 2. Call Twitch API to check stream status
            # 3. Compare with last known status
            # 4. Send notification if stream started/stopped
            
            # For now, this is a placeholder implementation
            pass
            
        except Exception as e:
            print(f"Error checking Twitch stream for {streamer.channel_id}: {e}")

    async def check_kick_stream(self, streamer: StreamNotification):
        """Check if a Kick channel is streaming"""
        try:
            # Kick doesn't have an official API, so we'll implement a web scraping approach
            # This is a simplified version - in reality, you'd need to parse the HTML properly
            
            # For now, this is a placeholder implementation
            # In a real implementation, you would:
            # 1. Fetch Kick channel page: https://kick.com/{channel_name}
            # 2. Parse HTML for live status indicator
            # 3. Compare with last known status
            # 4. Send notification if stream started/stopped
            
            # For now, this is a placeholder implementation
            pass
            
        except Exception as e:
            print(f"Error checking Kick stream for {streamer.channel_id}: {e}")

    async def update_streamer_last_video_id(self, streamer_id: int, video_id: str):
        """Update the last video ID for a streamer in the database"""
        db_manager = self.bot.db_manager
        async with db_manager.async_session() as session:
            from sqlalchemy.future import select
            result = await session.execute(
                select(StreamNotification).filter(StreamNotification.id == streamer_id)
            )
            streamer = result.scalar_one_or_none()
            
            if streamer:
                streamer.last_video_id = video_id
                await session.commit()

    async def send_youtube_notification(self, streamer: StreamNotification, title: str, video_id: str):
        """Send YouTube notification to the configured Discord channel"""
        # Get the Discord channel to send the notification
        discord_channel = self.bot.get_channel(streamer.discord_channel_id)
        if not discord_channel:
            print(f"Could not find the configured Discord channel (ID: {streamer.discord_channel_id})")
            return

        # Create embed for notification
        embed = discord.Embed(
            title=f"🎥 New YouTube Video!",
            description=f"[{title}](https://youtu.be/{video_id})",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Channel", value=streamer.channel_id, inline=True)
        embed.add_field(name="Platform", value="YouTube", inline=True)
        embed.set_footer(text=f"Powered by OpenMod v{self.bot.version}")
        embed.url = f"https://youtu.be/{video_id}"

        try:
            await discord_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Bot doesn't have permission to send messages in {discord_channel.mention}")
        except Exception as e:
            print(f"Error sending YouTube notification: {e}")

    @commands.group(name='stream', invoke_without_command=True)
    async def stream_group(self, ctx):
        """Manage stream notifications"""
        await ctx.send_help(ctx.command)

    @stream_group.command(name='add')
    @is_admin()
    async def add_streamer(self, ctx, platform: str, channel_id: str, discord_channel: discord.TextChannel = None):
        """Add a streamer to monitor"""
        platform = platform.lower()
        if platform not in ['youtube', 'twitch', 'kick']:
            await ctx.send("Platform must be one of: youtube, twitch, kick")
            return

        if discord_channel is None:
            discord_channel = ctx.channel

        # Get the database manager from the bot
        db_manager = self.bot.db_manager
        
        # Check if already exists
        async with db_manager.async_session() as session:
            from sqlalchemy.future import select
            result = await session.execute(
                select(StreamNotification).filter_by(
                    platform=platform,
                    channel_id=channel_id,
                    guild_id=ctx.guild.id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                await ctx.send(f"This {platform} channel is already being monitored!")
                return

            # Create new stream notification entry
            new_streamer = StreamNotification(
                guild_id=ctx.guild.id,
                discord_channel_id=discord_channel.id,
                platform=platform,
                channel_id=channel_id,
                added_by=ctx.author.id
            )
            
            session.add(new_streamer)
            await session.commit()

        await ctx.send(f"Added {platform} channel `{channel_id}` to monitoring in {discord_channel.mention}!")

    @stream_group.command(name='remove')
    @is_admin()
    async def remove_streamer(self, ctx, platform: str, channel_id: str):
        """Remove a streamer from monitoring"""
        platform = platform.lower()
        if platform not in ['youtube', 'twitch', 'kick']:
            await ctx.send("Platform must be one of: youtube, twitch, kick")
            return

        # Get the database manager from the bot
        db_manager = self.bot.db_manager
        
        # Find the streamer in the database
        async with db_manager.async_session() as session:
            from sqlalchemy.future import select
            result = await session.execute(
                select(StreamNotification).filter_by(
                    platform=platform,
                    channel_id=channel_id,
                    guild_id=ctx.guild.id
                )
            )
            streamer = result.scalar_one_or_none()

            if not streamer:
                await ctx.send(f"No {platform} channel `{channel_id}` found in monitoring!")
                return

            await session.delete(streamer)
            await session.commit()

        await ctx.send(f"Removed {platform} channel `{channel_id}` from monitoring!")

    @stream_group.command(name='list')
    @is_admin()
    async def list_streamers(self, ctx):
        """List all monitored streamers"""
        # Get the database manager from the bot
        db_manager = self.bot.db_manager
        
        # Get all streamers for this guild
        async with db_manager.async_session() as session:
            from sqlalchemy.future import select
            result = await session.execute(
                select(StreamNotification).filter_by(guild_id=ctx.guild.id)
            )
            streamers = result.scalars().all()
        
        if not streamers:
            await ctx.send("No streamers are currently being monitored.")
            return

        embed = discord.Embed(
            title="Monitored Streamers",
            color=discord.Color.blue()
        )

        for streamer in streamers:
            # Get the Discord channel name
            discord_channel = self.bot.get_channel(streamer.discord_channel_id)
            channel_name = discord_channel.name if discord_channel else f"#{streamer.discord_channel_id}"
            
            embed.add_field(
                name=f"{streamer.platform.title()} - {streamer.channel_id}",
                value=f"Notifications in: {channel_name}",
                inline=False
            )

        await ctx.send(embed=embed)

    @stream_group.command(name='test')
    @is_admin()
    async def test_notification(self, ctx, platform: str, channel_id: str):
        """Test sending a notification (for debugging)"""
        platform = platform.lower()
        if platform not in ['youtube', 'twitch', 'kick']:
            await ctx.send("Platform must be one of: youtube, twitch, kick")
            return

        # Get the database manager from the bot
        db_manager = self.bot.db_manager
        
        # Find the streamer in the database
        async with db_manager.async_session() as session:
            from sqlalchemy.future import select
            result = await session.execute(
                select(StreamNotification).filter_by(
                    platform=platform,
                    channel_id=channel_id,
                    guild_id=ctx.guild.id
                )
            )
            streamer = result.scalar_one_or_none()

            if not streamer:
                await ctx.send(f"No {platform} channel `{channel_id}` found in monitoring!")
                return

        # Get the Discord channel to send the notification
        discord_channel = self.bot.get_channel(streamer.discord_channel_id)
        if not discord_channel:
            await ctx.send(f"Could not find the configured Discord channel (ID: {streamer.discord_channel_id})")
            return

        # Send test notification
        embed = discord.Embed(
            title=f"🔴 {platform.title()} Stream Alert!",
            description=f"{channel_id} just went live!",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Platform", value=platform.title(), inline=True)
        embed.add_field(name="Channel", value=channel_id, inline=True)
        embed.set_footer(text=f"Powered by OpenMod v{self.bot.version}")

        try:
            await discord_channel.send(embed=embed)
            await ctx.send(f"Test notification sent to {discord_channel.mention}")
        except discord.Forbidden:
            await ctx.send(f"Bot doesn't have permission to send messages in {discord_channel.mention}")


async def setup(bot):
    await bot.add_cog(StreamNotifications(bot))