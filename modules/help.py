"""
Help module for OpenMod Discord Bot
Provides comprehensive help information about all commands
"""

import discord
from discord.ext import commands
from discord import app_commands

from core.version import __version__


class HelpCog(commands.Cog, name="Help"):
    """Help commands for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="help", description="Show help information about bot commands")
    @app_commands.describe(command="Specific command to get help for")
    async def help_command(self, ctx, command: str = None):
        """Show help information about bot commands."""
        if command:
            # Show help for a specific command
            cmd = self.bot.get_command(command)
            if cmd:
                embed = discord.Embed(
                    title=f"Help: {cmd.name}",
                    description=cmd.description or cmd.brief or "No description available",
                    color=0x5865F2
                )
                embed.add_field(name="Usage", value=f"`{ctx.clean_prefix}{cmd.signature}`", inline=False)
                
                # Add aliases if they exist
                if cmd.aliases:
                    embed.add_field(name="Aliases", value=", ".join([f"`{alias}`" for alias in cmd.aliases]), inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Command `{command}` not found.")
        else:
            # Show general help
            embed = discord.Embed(
                title=f"OpenMod v{__version__} - Help",
                description="OpenMod is a completely free and open-source Discord moderation bot with no paywalls.",
                color=0x5865F2
            )
            
            # Group commands by cog
            for cog_name, cog in self.bot.cogs.items():
                commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
                if commands_list:
                    command_names = ", ".join([f"`{cmd.name}`" for cmd in commands_list])
                    embed.add_field(name=cog_name, value=command_names, inline=False)
            
            # Add footer with version info
            embed.set_footer(text=f"OpenMod v{__version__} | 100% Free & Open Source | https://github.com/openmod")
            
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="version", description="Show the current bot version")
    async def version_command(self, ctx):
        """Show the current bot version."""
        embed = discord.Embed(
            title="OpenMod Version",
            description=f"Current version: **v{__version__}**",
            color=0x5865F2
        )
        embed.add_field(
            name="About OpenMod",
            value="A completely free and open-source Discord moderation bot with no paywalls.",
            inline=False
        )
        embed.add_field(
            name="GitHub",
            value="[OpenMod Repository](https://github.com/openmod/openmod)",
            inline=False
        )
        embed.set_footer(text="OpenMod - 100% Free & Open Source")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))