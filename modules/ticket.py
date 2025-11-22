"""
Ticket System Module for OpenMod Discord Bot
Version 2.0 - Enhanced ticket system with persistent views
"""
import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
from core.database import db
import aiosqlite

logger = logging.getLogger(__name__)

@dataclass
class TicketConfig:
    """Configuration for ticket system"""
    category_id: int
    log_channel_id: int
    support_role_id: int
    max_tickets_per_user: int = 3
    transcript_channel_id: Optional[int] = None

class TicketView(discord.ui.View):
    """Persistent ticket creation view"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="ticket:create"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class TicketModal(discord.ui.Modal, title="Create Ticket"):
    """Modal for ticket creation"""
    
    issue_type = discord.ui.Select(
        placeholder="Select issue type...",
        options=[
            discord.SelectOption(label="General Support", value="general", description="General questions or help"),
            discord.SelectOption(label="Report User", value="report", description="Report a user for violations"),
            discord.SelectOption(label="Technical Issue", value="tech", description="Technical problems with the server"),
            discord.SelectOption(label="Appeal", value="appeal", description="Appeal a moderation decision"),
            discord.SelectOption(label="Other", value="other", description="Other issues not listed above")
        ]
    )
    
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Briefly describe your issue...",
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.long,
        placeholder="Provide detailed information about your issue...",
        max_length=1000
    )
    
    def __init__(self):
        super().__init__()
        self.add_item(self.issue_type)
    
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has too many open tickets
        open_tickets = await db.get_user_open_tickets(user.id)
        if open_tickets >= 3:  # Max 3 tickets per user
            await interaction.response.send_message(
                "You already have 3 open tickets. Please close existing tickets before creating a new one.",
                ephemeral=True
            )
            return
        
        # Get ticket configuration
        config = await db.get_ticket_config(guild.id)
        if not config:
            await interaction.response.send_message(
                "Ticket system is not configured for this server. Contact an administrator.",
                ephemeral=True
            )
            return
        
        # Create ticket channel
        category = discord.utils.get(guild.categories, id=config['category_id'])
        if not category:
            await interaction.response.send_message(
                "Ticket category not found. Contact an administrator.",
                ephemeral=True
            )
            return
        
        # Create unique channel name
        channel_name = f"ticket-{user.name}-{len(open_tickets) + 1}".lower().replace(" ", "-")
        
        try:
            # Create ticket channel
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    user: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
                }
            )
            
            # Add support role permissions if exists
            if config['support_role_id']:
                support_role = discord.utils.get(guild.roles, id=config['support_role_id'])
                if support_role:
                    await ticket_channel.set_permissions(
                        support_role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
            
            # Create ticket in database
            ticket_id = await db.create_ticket(
                guild_id=guild.id,
                channel_id=ticket_channel.id,
                user_id=user.id,
                issue_type=self.issue_type.values[0],
                subject=str(self.subject),
                description=str(self.description)
            )
            
            # Send ticket message
            embed = discord.Embed(
                title="🎫 New Ticket Created",
                description=f"**Issue Type:** {self.issue_type.values[0].title()}\n"
                           f"**Subject:** {self.subject}\n"
                           f"**Description:** {self.description}\n\n"
                           f"**Created by:** {user.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
            embed.add_field(name="Status", value="Open", inline=True)
            
            close_button = CloseTicketButton(ticket_id)
            view = discord.ui.View()
            view.add_item(close_button)
            
            await ticket_channel.send(embed=embed, view=view)
            
            # Notify user
            await interaction.response.send_message(
                f"Ticket created successfully! Check {ticket_channel.mention}",
                ephemeral=True
            )
            
            # Log ticket creation
            if config['log_channel_id']:
                log_channel = discord.utils.get(guild.text_channels, id=config['log_channel_id'])
                if log_channel:
                    log_embed = discord.Embed(
                        title="Ticket Created",
                        description=f"{user.mention} created ticket {ticket_channel.mention}",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    await log_channel.send(embed=log_embed)
                    
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message(
                "An error occurred while creating your ticket. Please contact an administrator.",
                ephemeral=True
            )

class CloseTicketButton(discord.ui.Button):
    """Button to close a ticket"""
    
    def __init__(self, ticket_id: int):
        super().__init__(
            label="Close Ticket",
            style=discord.ButtonStyle.red,
            emoji="🔒",
            custom_id=f"ticket:close:{ticket_id}"
        )
        self.ticket_id = ticket_id
    
    async def callback(self, interaction: discord.Interaction):
        # Check permissions
        if not (interaction.user.guild_permissions.manage_channels or 
                interaction.user.guild_permissions.administrator):
            # Check if user is the ticket creator
            ticket = await db.get_ticket(self.ticket_id)
            if ticket['user_id'] != interaction.user.id:
                await interaction.response.send_message(
                    "You don't have permission to close this ticket.",
                    ephemeral=True
                )
                return
        
        # Confirm closure
        confirm_view = ConfirmCloseView(self.ticket_id)
        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=confirm_view,
            ephemeral=True
        )

class ConfirmCloseView(discord.ui.View):
    """Confirmation view for closing tickets"""
    
    def __init__(self, ticket_id: int):
        super().__init__(timeout=30)
        self.ticket_id = ticket_id
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get ticket info
        ticket = await db.get_ticket(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return
        
        # Get channel and guild
        guild = interaction.guild
        channel = discord.utils.get(guild.text_channels, id=ticket['channel_id'])
        user = discord.utils.get(guild.members, id=ticket['user_id'])
        
        if not channel:
            await interaction.response.send_message("Ticket channel not found.", ephemeral=True)
            return
        
        # Get transcript if enabled
        if ticket.get('transcript_channel_id'):
            transcript = await self.get_transcript(channel)
            transcript_channel = discord.utils.get(
                guild.text_channels, 
                id=ticket.get('transcript_channel_id')
            )
            if transcript_channel:
                await transcript_channel.send(transcript)
        
        # Close ticket in database
        await db.close_ticket(self.ticket_id)
        
        # Send confirmation
        await interaction.response.send_message("Ticket closed successfully!", ephemeral=True)
        
        # Delete channel after delay
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except discord.NotFound:
            pass  # Channel already deleted
    
    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket closure cancelled.", ephemeral=True)
    
    async def get_transcript(self, channel: discord.TextChannel) -> str:
        """Get transcript of ticket channel"""
        messages = []
        async for message in channel.history(limit=100, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(f"[{timestamp}] {message.author}: {message.content}")
        
        transcript = "\n".join(reversed(messages))
        return f"```\nTicket Transcript - Channel: {channel.name}\n\n{transcript}\n```"

class TicketCog(commands.Cog):
    """Ticket System Cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="ticket", aliases=["tickets"], invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def ticket_group(self, ctx):
        """Ticket management commands"""
        await ctx.send_help(ctx.command)
    
    @ticket_group.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx, category: discord.CategoryChannel, 
                          support_role: discord.Role = None, 
                          log_channel: discord.TextChannel = None):
        """Setup ticket system"""
        # Create the ticket category if it doesn't exist
        if not category:
            category = await ctx.guild.create_category("Tickets")
        
        # Save configuration to database
        await db.set_ticket_config(
            guild_id=ctx.guild.id,
            category_id=category.id,
            support_role_id=support_role.id if support_role else None,
            log_channel_id=log_channel.id if log_channel else None
        )
        
        # Create persistent ticket view
        view = TicketView()
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Click the button below to create a support ticket.\n"
                       "Our support team will assist you as soon as possible.",
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed, view=view)
        
        await ctx.send(f"Ticket system setup complete! Created in {category.mention}")
    
    @ticket_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add_user(self, ctx, ticket_channel: discord.TextChannel, user: discord.Member):
        """Add a user to a ticket channel"""
        # Check if channel is a ticket
        ticket = await db.get_ticket_by_channel(ticket_channel.id)
        if not ticket:
            await ctx.send("This channel is not a ticket channel.")
            return
        
        # Add user to channel permissions
        await ticket_channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
        
        await ctx.send(f"Added {user.mention} to the ticket.")
    
    @ticket_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove_user(self, ctx, ticket_channel: discord.TextChannel, user: discord.Member):
        """Remove a user from a ticket channel"""
        # Check if channel is a ticket
        ticket = await db.get_ticket_by_channel(ticket_channel.id)
        if not ticket:
            await ctx.send("This channel is not a ticket channel.")
            return
        
        # Remove user from channel permissions
        await ticket_channel.set_permissions(user, overwrite=None)
        
        await ctx.send(f"Removed {user.mention} from the ticket.")

async def setup(bot):
    """Setup function for the ticket cog"""
    await bot.add_cog(TicketCog(bot))