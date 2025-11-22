"""
Reaction Roles Module for OpenMod Discord Bot
Version 2.0 - Enhanced reaction roles with persistent views
"""
import discord
from discord.ext import commands
import logging
from typing import Dict, List, Optional
from core.database import db

logger = logging.getLogger(__name__)

class ReactionRoleView(discord.ui.View):
    """Persistent reaction role view"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
        self.reaction_roles = {}
    
    def add_reaction_role(self, emoji: str, role_id: int):
        """Add a reaction role button to the view"""
        button = ReactionRoleButton(emoji, role_id)
        self.add_item(button)
        self.reaction_roles[emoji] = role_id

class ReactionRoleButton(discord.ui.Button):
    """Button for reaction roles"""
    
    def __init__(self, emoji: str, role_id: int):
        super().__init__(
            label=" ",
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            custom_id=f"reaction_role:{emoji}:{role_id}"
        )
        self.role_id = role_id
        self.emoji = emoji
    
    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        
        # Get role
        role = discord.utils.get(guild.roles, id=self.role_id)
        if not role:
            await interaction.response.send_message(
                "This role no longer exists. Contact an administrator.", 
                ephemeral=True
            )
            return
        
        # Check if user already has the role
        if role in member.roles:
            try:
                await member.remove_roles(role)
                await interaction.response.send_message(
                    f"Removed role: {role.mention}", 
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to remove that role.", 
                    ephemeral=True
                )
        else:
            try:
                await member.add_roles(role)
                await interaction.response.send_message(
                    f"Added role: {role.mention}", 
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to add that role.", 
                    ephemeral=True
                )

class ReactionRoleCog(commands.Cog):
    """Reaction Roles Cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="reaction", aliases=["rr", "reactionrole"], invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def reaction_group(self, ctx):
        """Reaction role management commands"""
        await ctx.send_help(ctx.command)
    
    @reaction_group.command(name="create")
    @commands.has_permissions(manage_roles=True)
    async def reaction_create(self, ctx, message: discord.Message, 
                             *args):
        """
        Create reaction roles
        Usage: !reaction create <message_id> <emoji> <role> [emoji role]...
        Example: !reaction create 123456789 ✅ @Member 🎮 @Gamer
        """
        if len(args) % 2 != 0:
            await ctx.send("Please provide emoji-role pairs (even number of arguments).")
            return
        
        # Create reaction role pairs
        reaction_pairs = []
        for i in range(0, len(args), 2):
            emoji = args[i]
            role_name = args[i + 1]
            
            # Find role by name or ID
            role = discord.utils.get(ctx.guild.roles, name=role_name) or \
                   discord.utils.get(ctx.guild.roles, id=int(role_name.replace("<@&", "").replace(">", "")))
            
            if not role:
                await ctx.send(f"Role '{role_name}' not found.")
                return
            
            reaction_pairs.append((emoji, role.id))
        
        # Add reactions to message
        for emoji, _ in reaction_pairs:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                await ctx.send(f"Invalid emoji: {emoji}")
                return
        
        # Create persistent view for the message
        view = ReactionRoleView()
        for emoji, role_id in reaction_pairs:
            view.add_reaction_role(emoji, role_id)
        
        # Store in database
        await db.create_reaction_roles(
            guild_id=ctx.guild.id,
            message_id=message.id,
            channel_id=message.channel.id,
            reactions=[{"emoji": emoji, "role_id": role_id} for emoji, role_id in reaction_pairs]
        )
        
        # Send the view to the message (or update it)
        await ctx.send(f"Reaction roles created for message {message.jump_url}")
    
    @reaction_group.command(name="setup")
    @commands.has_permissions(manage_roles=True)
    async def reaction_setup(self, ctx, channel: discord.TextChannel, title: str, 
                            description: str, *args):
        """
        Setup a reaction role message with embed
        Usage: !reaction setup <channel> <title> <description> <emoji> <role> [emoji role]...
        """
        if len(args) % 2 != 0:
            await ctx.send("Please provide emoji-role pairs (even number of arguments).")
            return
        
        # Create reaction role pairs
        reaction_pairs = []
        for i in range(0, len(args), 2):
            emoji = args[i]
            role_name = args[i + 1]
            
            # Find role by name or ID
            role = discord.utils.get(ctx.guild.roles, name=role_name) or \
                   discord.utils.get(ctx.guild.roles, id=int(role_name.replace("<@&", "").replace(">", "")))
            
            if not role:
                await ctx.send(f"Role '{role_name}' not found.")
                return
            
            reaction_pairs.append((emoji, role.id))
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        # Add fields for each reaction role
        for emoji, role_id in reaction_pairs:
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            if role:
                embed.add_field(
                    name=f"{emoji} {role.name}",
                    value=f"React to get the {role.mention} role",
                    inline=False
                )
        
        # Create persistent view
        view = ReactionRoleView()
        for emoji, role_id in reaction_pairs:
            view.add_reaction_role(emoji, role_id)
        
        # Send message with embed and view
        sent_message = await channel.send(embed=embed, view=view)
        
        # Store in database
        await db.create_reaction_roles(
            guild_id=ctx.guild.id,
            message_id=sent_message.id,
            channel_id=channel.id,
            reactions=[{"emoji": emoji, "role_id": role_id} for emoji, role_id in reaction_pairs]
        )
        
        await ctx.send(f"Reaction role setup complete! Message sent to {channel.mention}")
    
    @reaction_group.command(name="list")
    @commands.has_permissions(manage_roles=True)
    async def reaction_list(self, ctx):
        """List all reaction roles in this server"""
        reaction_roles = await db.get_guild_reaction_roles(ctx.guild.id)
        
        if not reaction_roles:
            await ctx.send("No reaction roles found in this server.")
            return
        
        embed = discord.Embed(
            title="Reaction Roles in this Server",
            color=discord.Color.blue()
        )
        
        for rr in reaction_roles:
            channel = discord.utils.get(ctx.guild.text_channels, id=rr['channel_id'])
            message_link = f"[Message]({channel.jump_url}/{rr['message_id']})" if channel else "Unknown"
            
            reactions_str = ", ".join([
                f"{r['emoji']} → <@&{r['role_id']}>"
                for r in rr['reactions']
            ])
            
            embed.add_field(
                name=f"Channel: {channel.name if channel else 'Unknown'}",
                value=f"{message_link}\nReactions: {reactions_str}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @reaction_group.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def reaction_remove(self, ctx, message_id: int):
        """Remove reaction roles from a message"""
        success = await db.delete_reaction_roles(ctx.guild.id, message_id)
        
        if success:
            await ctx.send("Reaction roles removed successfully.")
        else:
            await ctx.send("No reaction roles found for that message.")

async def setup(bot):
    """Setup function for the reaction roles cog"""
    await bot.add_cog(ReactionRoleCog(bot))