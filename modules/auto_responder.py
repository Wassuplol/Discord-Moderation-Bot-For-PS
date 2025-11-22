"""
Auto-Responder Module for OpenMod Discord Bot
Version 2.0 - Enhanced auto-responder with regex support
"""
import discord
from discord.ext import commands
import re
import logging
from typing import List, Dict, Any
from core.database import db

logger = logging.getLogger(__name__)

class AutoResponderCog(commands.Cog):
    """Auto-responder Cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="autoresponder", aliases=["ar", "auto"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_group(self, ctx):
        """Auto-responder management commands"""
        await ctx.send_help(ctx.command)
    
    @autoresponder_group.command(name="add")
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_add(self, ctx, trigger: str, *, response: str):
        """Add an auto-responder"""
        success = await db.create_auto_responder(
            guild_id=ctx.guild.id,
            trigger=trigger,
            response=response
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Auto-Responder Added",
                description=f"**Trigger:** `{trigger}`\n**Response:** {response}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to add auto-responder.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @autoresponder_group.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_list(self, ctx):
        """List all auto-responders for this server"""
        auto_responders = await db.get_guild_auto_responders(ctx.guild.id)
        
        if not auto_responders:
            embed = discord.Embed(
                title="📋 Auto-Responders",
                description="No auto-responders found for this server.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 Auto-Responders",
            color=discord.Color.blue()
        )
        
        for ar in auto_responders[:25]:  # Limit to first 25
            embed.add_field(
                name=f"`{ar['trigger']}`",
                value=ar['response'][:100] + "..." if len(ar['response']) > 100 else ar['response'],
                inline=False
            )
        
        if len(auto_responders) > 25:
            embed.set_footer(text=f"Showing first 25 of {len(auto_responders)} auto-responders")
        
        await ctx.send(embed=embed)
    
    @autoresponder_group.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_remove(self, ctx, trigger: str):
        """Remove an auto-responder (not implemented in DB yet, placeholder)"""
        # This would require a delete method in the database
        embed = discord.Embed(
            title="ℹ️ Info",
            description="Removing auto-responders is not yet implemented in the database.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and respond to triggers"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        # Get all auto-responders for this guild
        auto_responders = await db.get_guild_auto_responders(message.guild.id)
        
        for ar in auto_responders:
            trigger = ar['trigger']
            response = ar['response']
            
            # Check if message contains the trigger
            if self._check_trigger(message.content, trigger, ar['case_sensitive'], ar['regex']):
                try:
                    # Send the response
                    await message.channel.send(response)
                    break  # Only respond to the first match
                except discord.Forbidden:
                    # Can't send message in this channel
                    pass
                except Exception as e:
                    logger.error(f"Error sending auto-responder: {e}")
    
    def _check_trigger(self, message_content: str, trigger: str, case_sensitive: bool, regex: bool) -> bool:
        """Check if message content matches the trigger"""
        if regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                return bool(re.search(trigger, message_content, flags))
            except re.error:
                # Invalid regex, fallback to simple check
                pass
        
        if case_sensitive:
            return trigger.lower() in message_content.lower()
        else:
            return trigger in message_content

async def setup(bot):
    """Setup function for the auto-responder cog"""
    await bot.add_cog(AutoResponderCog(bot))