"""
Unit tests for the moderation module
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from modules.moderation import ModerationCog


class TestModerationCog(unittest.IsolatedAsyncioTestCase):
    """Test cases for the ModerationCog"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock bot
        self.bot = AsyncMock()
        self.bot.db_manager = AsyncMock()
        self.bot.get_guild_config = AsyncMock()
        
        # Create a mock context
        self.ctx = AsyncMock(spec=commands.Context)
        self.ctx.guild = AsyncMock(spec=discord.Guild)
        self.ctx.author = AsyncMock(spec=discord.Member)
        self.ctx.channel = AsyncMock(spec=discord.TextChannel)
        
        # Create mock member to be moderated
        self.member = AsyncMock(spec=discord.Member)
        self.member.id = 123456789
        self.member.bot = False
        self.member.top_role = AsyncMock()
        self.ctx.guild.owner = self.ctx.author  # Make author the guild owner for tests
        
        # Create the cog
        self.cog = ModerationCog(self.bot)
    
    async def test_warn_command_success(self):
        """Test that the warn command works correctly"""
        # Mock the database logging
        self.bot.db_manager.log_moderation_action.return_value = True
        
        # Mock the member's send method
        self.member.send = AsyncMock()
        
        # Set up context expectations
        self.ctx.author.id = 987654321
        self.ctx.guild.id = 111111111
        self.ctx.send = AsyncMock()
        
        # Call the warn command
        await self.cog.warn(self.ctx, self.member, reason="Test reason")
        
        # Verify that the database was called correctly
        self.bot.db_manager.log_moderation_action.assert_called_once_with(
            guild_id=111111111,
            user_id=123456789,
            moderator_id=987654321,
            action_type='warn',
            reason="Test reason"
        )
        
        # Verify that the context send was called
        self.ctx.send.assert_called()
        
        # Verify that the member was sent a DM
        self.member.send.assert_called()
    
    async def test_kick_command_success(self):
        """Test that the kick command works correctly"""
        # Mock the database logging
        self.bot.db_manager.log_moderation_action.return_value = True
        
        # Mock the member's kick method
        self.member.kick = AsyncMock()
        self.member.send = AsyncMock()
        
        # Set up context expectations
        self.ctx.author.id = 987654321
        self.ctx.guild.id = 111111111
        self.ctx.send = AsyncMock()
        
        # Call the kick command
        await self.cog.kick(self.ctx, self.member, reason="Test reason")
        
        # Verify that the database was called correctly
        self.bot.db_manager.log_moderation_action.assert_called_once_with(
            guild_id=111111111,
            user_id=123456789,
            moderator_id=987654321,
            action_type='kick',
            reason="Test reason"
        )
        
        # Verify that the member was kicked
        self.member.kick.assert_called_once()
        
        # Verify that the context send was called
        self.ctx.send.assert_called()
    
    async def test_ban_command_success(self):
        """Test that the ban command works correctly"""
        # Mock the database logging
        self.bot.db_manager.log_moderation_action.return_value = True
        
        # Mock the member's ban method
        self.member.ban = AsyncMock()
        self.member.send = AsyncMock()
        
        # Set up context expectations
        self.ctx.author.id = 987654321
        self.ctx.guild.id = 111111111
        self.ctx.send = AsyncMock()
        
        # Call the ban command
        await self.cog.ban(self.ctx, self.member, reason="Test reason")
        
        # Verify that the database was called correctly
        self.bot.db_manager.log_moderation_action.assert_called_once_with(
            guild_id=111111111,
            user_id=123456789,
            moderator_id=987654321,
            action_type='ban',
            reason="Test reason"
        )
        
        # Verify that the member was banned
        self.member.ban.assert_called_once()
        
        # Verify that the context send was called
        self.ctx.send.assert_called()


if __name__ == '__main__':
    unittest.main()