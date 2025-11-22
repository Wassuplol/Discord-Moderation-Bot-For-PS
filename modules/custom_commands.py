"""
Custom Commands Module for OpenMod Discord Bot
Version 2.0 - Enhanced custom commands with usage tracking
"""
import discord
from discord.ext import commands
import logging
from typing import List, Dict, Any
from core.database import db

logger = logging.getLogger(__name__)

class CustomCommandsCog(commands.Cog):
    """Custom Commands Cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="custom", aliases=["cc", "cmd"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def custom_group(self, ctx):
        """Custom command management commands"""
        await ctx.send_help(ctx.command)
    
    @custom_group.command(name="create")
    @commands.has_permissions(manage_messages=True)
    async def custom_create(self, ctx, command_name: str, *, response: str):
        """Create a custom command"""
        # Validate command name
        if not command_name.isalnum() or len(command_name) < 2 or len(command_name) > 32:
            embed = discord.Embed(
                title="❌ Invalid Command Name",
                description="Command name must be 2-32 characters long and contain only letters and numbers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Check if command already exists
        existing_cmd = await db.get_custom_command(ctx.guild.id, command_name)
        if existing_cmd:
            embed = discord.Embed(
                title="❌ Command Already Exists",
                description=f"Command `{command_name}` already exists.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Create the command
        success = await db.create_custom_command(
            guild_id=ctx.guild.id,
            command_name=command_name,
            response=response,
            created_by=ctx.author.id
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Custom Command Created",
                description=f"**Command:** `!{command_name}`\n**Response:** {response}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to create custom command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @custom_group.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def custom_list(self, ctx):
        """List all custom commands for this server"""
        commands = await db.get_guild_custom_commands(ctx.guild.id)
        
        if not commands:
            embed = discord.Embed(
                title="📋 Custom Commands",
                description="No custom commands found for this server.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 Custom Commands",
            color=discord.Color.blue()
        )
        
        for cmd in commands[:25]:  # Limit to first 25
            embed.add_field(
                name=f"!{cmd['command_name']} (Used {cmd['uses']} times)",
                value=cmd['response'][:100] + "..." if len(cmd['response']) > 100 else cmd['response'],
                inline=False
            )
        
        if len(commands) > 25:
            embed.set_footer(text=f"Showing first 25 of {len(commands)} custom commands")
        
        await ctx.send(embed=embed)
    
    @custom_group.command(name="info")
    @commands.has_permissions(manage_messages=True)
    async def custom_info(self, ctx, command_name: str):
        """Get information about a custom command"""
        cmd = await db.get_custom_command(ctx.guild.id, command_name)
        
        if not cmd:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"Custom command `!{command_name}` does not exist.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        creator = self.bot.get_user(cmd['created_by']) or await self.bot.fetch_user(cmd['created_by'])
        
        embed = discord.Embed(
            title=f"ℹ️ Custom Command: !{cmd['command_name']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Response", value=cmd['response'], inline=False)
        embed.add_field(name="Created By", value=creator.mention if creator else f"<@{cmd['created_by']}>", inline=True)
        embed.add_field(name="Uses", value=cmd['uses'], inline=True)
        embed.add_field(name="Created At", value=cmd['created_at'].strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for custom commands"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check if message starts with bot prefix
        prefix = self.bot.command_prefix
        if not message.content.startswith(prefix):
            return
        
        # Extract command name (without prefix)
        content = message.content[len(prefix):].strip()
        if ' ' in content:
            command_name = content.split(' ')[0].lower()
        else:
            command_name = content.lower()
        
        # Check if it's a custom command
        cmd = await db.get_custom_command(message.guild.id, command_name)
        
        if cmd:
            # Send the response
            try:
                await message.channel.send(cmd['response'])
                
                # Increment usage count
                await db.increment_custom_command_usage(cmd['id'])
                
                # Log the usage
                logger.info(f"Custom command '{command_name}' used in {message.guild.name} by {message.author.name}")
            except discord.Forbidden:
                # Can't send message in this channel
                pass
            except Exception as e:
                logger.error(f"Error sending custom command response: {e}")

async def setup(bot):
    """Setup function for the custom commands cog"""
    await bot.add_cog(CustomCommandsCog(bot))