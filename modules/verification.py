"""
Member Verification Module for OpenMod Discord Bot
Version 2.0 - Enhanced member verification system
"""
import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional
from core.database import db

logger = logging.getLogger(__name__)

class VerificationView(discord.ui.View):
    """Verification view with button"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="verification:verify"
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Add verified role to user
        guild = interaction.guild
        user = interaction.user
        
        # Get verification config (we'll implement this later)
        # For now, just log the verification
        success = await db.create_member_verification(
            guild_id=guild.id,
            user_id=user.id,
            verification_method='button'
        )
        
        if success:
            await db.verify_member(guild.id, user.id)
            await interaction.response.send_message(
                "✅ You have been verified!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Error during verification.",
                ephemeral=True
            )

class VerificationCog(commands.Cog):
    """Verification Cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="verification", aliases=["verify"], invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def verification_group(self, ctx):
        """Verification management commands"""
        await ctx.send_help(ctx.command)
    
    @verification_group.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def verification_setup(self, ctx, role: discord.Role, channel: discord.TextChannel = None):
        """Setup verification system"""
        if not channel:
            channel = ctx.channel
        
        # Create verification message with embed and button
        embed = discord.Embed(
            title="🔐 Verification Required",
            description="Please click the button below to verify yourself and gain access to the server.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Why verify?",
            value="Verification helps us keep the server safe from bots and spam.",
            inline=False
        )
        
        view = VerificationView()
        message = await channel.send(embed=embed, view=view)
        
        await ctx.send(f"✅ Verification system set up in {channel.mention}")
    
    @verification_group.command(name="status")
    @commands.has_permissions(manage_roles=True)
    async def verification_status(self, ctx, member: discord.Member = None):
        """Check verification status of a member"""
        if not member:
            member = ctx.author
        
        verification = await db.get_member_verification(ctx.guild.id, member.id)
        
        if not verification:
            embed = discord.Embed(
                title="ℹ️ Verification Status",
                description=f"{member.mention} has not been verified yet.",
                color=discord.Color.orange()
            )
        elif verification['verified']:
            embed = discord.Embed(
                title="✅ Verification Status",
                description=f"{member.mention} is verified.",
                color=discord.Color.green()
            )
            if verification['verified_at']:
                embed.add_field(
                    name="Verified At",
                    value=verification['verified_at'].strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
        else:
            embed = discord.Embed(
                title="⏳ Verification Status",
                description=f"{member.mention} has started verification but not completed it.",
                color=discord.Color.orange()
            )
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member joins for verification"""
        # Log the join for verification tracking
        await db.create_member_verification(
            guild_id=member.guild.id,
            user_id=member.id,
            verification_method='join'
        )
        
        # Optionally DM the user with verification instructions
        try:
            embed = discord.Embed(
                title="🔐 Server Verification",
                description=f"Welcome to {member.guild.name}! Please verify yourself by using the verify button in the server.",
                color=discord.Color.blue()
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            # User has DMs disabled
            pass
        except Exception as e:
            logger.error(f"Error sending verification DM: {e}")

async def setup(bot):
    """Setup function for the verification cog"""
    await bot.add_cog(VerificationCog(bot))