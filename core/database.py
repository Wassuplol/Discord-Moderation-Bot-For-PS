"""
Database module for OpenMod bot
Handles database connections, models, and operations
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, BigInteger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select

from core.config import Config

# SQLAlchemy setup
Base = declarative_base()

class GuildConfig(Base):
    """Guild configuration model"""
    __tablename__ = 'guild_configs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, unique=True, nullable=False)
    prefix = Column(String(10), default=Config.BOT_PREFIX)
    moderation_channel_id = Column(BigInteger)
    message_log_channel_id = Column(BigInteger)
    member_log_channel_id = Column(BigInteger)
    auto_mod_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    """User model for storing user data"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)  # For soft deletion

class ModerationAction(Base):
    """Moderation action model"""
    __tablename__ = 'moderation_actions'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)  # The user being moderated
    moderator_id = Column(BigInteger, nullable=False)  # The moderator
    action_type = Column(String(20), nullable=False)  # warn, mute, kick, ban, etc.
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # For temporary actions
    active = Column(Boolean, default=True)

class MessageLog(Base):
    """Message log model for edit/delete tracking"""
    __tablename__ = 'message_logs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, unique=True, nullable=False)
    content_before = Column(Text)
    content_after = Column(Text)
    action_type = Column(String(10), nullable=False)  # edit, delete
    created_at = Column(DateTime, default=datetime.utcnow)

class AutoModRule(Base):
    """Auto-moderation rule model"""
    __tablename__ = 'automod_rules'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    rule_type = Column(String(50), nullable=False)  # spam, mention_spam, word_filter, etc.
    enabled = Column(Boolean, default=True)
    settings = Column(Text)  # JSON string for rule-specific settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """Database manager class for handling connections and operations"""
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.async_session = None
        self.logger = logging.getLogger('openmod.database')
        
    async def init(self):
        """Initialize the database connection and create tables if they don't exist"""
        try:
            # Determine database type and create appropriate engine
            db_config = Config.get_database_config()
            
            if db_config['type'] == 'postgresql':
                # PostgreSQL async engine
                self.async_engine = create_async_engine(
                    db_config['url'],
                    pool_size=db_config['pool_size'],
                    pool_timeout=db_config['pool_timeout'],
                    pool_recycle=db_config['pool_recycle']
                )
            else:
                # SQLite async engine
                self.async_engine = create_async_engine(
                    db_config['url'],
                    echo=False  # Set to True for SQL query logging
                )
            
            # Create async session
            self.async_session = sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
            self.logger.info(f"Database initialized successfully with {db_config['type']} backend")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close the database connection"""
        if self.async_engine:
            await self.async_engine.dispose()
            self.logger.info("Database connection closed")
    
    async def get_guild_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get guild configuration from database"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(GuildConfig).filter(GuildConfig.guild_id == guild_id)
                )
                config = result.scalar_one_or_none()
                
                if config:
                    return {
                        'prefix': config.prefix,
                        'moderation_channel_id': config.moderation_channel_id,
                        'message_log_channel_id': config.message_log_channel_id,
                        'member_log_channel_id': config.member_log_channel_id,
                        'auto_mod_enabled': config.auto_mod_enabled
                    }
                return None
            except Exception as e:
                self.logger.error(f"Error getting guild config: {e}")
                return None
    
    async def create_guild_config(self, guild_id: int, **kwargs) -> bool:
        """Create a new guild configuration"""
        async with self.async_session() as session:
            try:
                config = GuildConfig(
                    guild_id=guild_id,
                    prefix=kwargs.get('prefix', Config.BOT_PREFIX),
                    moderation_channel_id=kwargs.get('moderation_channel_id'),
                    message_log_channel_id=kwargs.get('message_log_channel_id'),
                    member_log_channel_id=kwargs.get('member_log_channel_id'),
                    auto_mod_enabled=kwargs.get('auto_mod_enabled', True)
                )
                session.add(config)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error creating guild config: {e}")
                await session.rollback()
                return False
    
    async def log_moderation_action(self, guild_id: int, user_id: int, moderator_id: int, 
                                   action_type: str, reason: str = None, 
                                   expires_at: datetime = None) -> bool:
        """Log a moderation action"""
        async with self.async_session() as session:
            try:
                action = ModerationAction(
                    guild_id=guild_id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action_type=action_type,
                    reason=reason,
                    expires_at=expires_at
                )
                session.add(action)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error logging moderation action: {e}")
                await session.rollback()
                return False
    
    async def get_recent_moderation_actions(self, user_id: int, guild_id: int, 
                                           days: int = 30) -> List[Dict[str, Any]]:
        """Get recent moderation actions for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(ModerationAction)
                    .filter(
                        ModerationAction.user_id == user_id,
                        ModerationAction.guild_id == guild_id,
                        ModerationAction.created_at >= cutoff_date
                    )
                    .order_by(ModerationAction.created_at.desc())
                )
                actions = result.scalars().all()
                
                return [
                    {
                        'id': action.id,
                        'action_type': action.action_type,
                        'reason': action.reason,
                        'moderator_id': action.moderator_id,
                        'created_at': action.created_at,
                        'expires_at': action.expires_at
                    }
                    for action in actions
                ]
            except Exception as e:
                self.logger.error(f"Error getting moderation actions: {e}")
                return []
    
    async def cleanup_old_logs(self):
        """Clean up old logs based on retention settings"""
        message_cutoff = datetime.utcnow() - timedelta(days=Config.MESSAGE_LOG_RETENTION_DAYS)
        mod_cutoff = datetime.utcnow() - timedelta(days=Config.MODERATION_LOG_RETENTION_DAYS)
        
        async with self.async_session() as session:
            try:
                # Delete old message logs
                result = await session.execute(
                    "DELETE FROM message_logs WHERE created_at < :cutoff",
                    {"cutoff": message_cutoff}
                )
                message_deleted = result.rowcount
                
                # Delete old moderation logs that are inactive and expired
                result = await session.execute(
                    "DELETE FROM moderation_actions WHERE created_at < :cutoff AND active = false",
                    {"cutoff": mod_cutoff}
                )
                mod_deleted = result.rowcount
                
                await session.commit()
                
                self.logger.info(f"Cleaned up {message_deleted} old message logs and {mod_deleted} old moderation logs")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up old logs: {e}")
                await session.rollback()
    
    async def get_user_data(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get user data from the database"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(User).filter(
                        User.user_id == user_id,
                        User.guild_id == guild_id
                    )
                )
                user = result.scalar_one_or_none()
                
                if user and not user.deleted_at:  # Don't return soft-deleted users
                    return {
                        'id': user.id,
                        'user_id': user.user_id,
                        'guild_id': user.guild_id,
                        'created_at': user.created_at
                    }
                return None
            except Exception as e:
                self.logger.error(f"Error getting user data: {e}")
                return None

    async def create_ticket(self, guild_id: int, channel_id: int, user_id: int, 
                          issue_type: str, subject: str, description: str) -> bool:
        """Create a new ticket"""
        async with self.async_session() as session:
            try:
                ticket = Ticket(
                    guild_id=guild_id,
                    channel_id=channel_id,
                    user_id=user_id,
                    issue_type=issue_type,
                    subject=subject,
                    description=description
                )
                session.add(ticket)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error creating ticket: {e}")
                await session.rollback()
                return False

    async def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """Get a ticket by ID"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(Ticket).filter(Ticket.id == ticket_id)
                )
                ticket = result.scalar_one_or_none()
                return ticket.to_dict() if ticket else None
            except Exception as e:
                self.logger.error(f"Error getting ticket: {e}")
                return None

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get a ticket by channel ID"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(Ticket).filter(Ticket.channel_id == channel_id)
                )
                ticket = result.scalar_one_or_none()
                return ticket.to_dict() if ticket else None
            except Exception as e:
                self.logger.error(f"Error getting ticket by channel: {e}")
                return None

    async def get_user_open_tickets(self, user_id: int) -> int:
        """Get number of open tickets for a user"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(Ticket).filter(
                        Ticket.user_id == user_id,
                        Ticket.status == 'open'
                    )
                )
                tickets = result.scalars().all()
                return len(tickets)
            except Exception as e:
                self.logger.error(f"Error getting user open tickets: {e}")
                return 0

    async def close_ticket(self, ticket_id: int) -> bool:
        """Close a ticket"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(Ticket).filter(Ticket.id == ticket_id)
                )
                ticket = result.scalar_one_or_none()
                
                if ticket:
                    ticket.status = 'closed'
                    ticket.closed_at = datetime.utcnow()
                    await session.commit()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Error closing ticket: {e}")
                await session.rollback()
                return False

    async def set_ticket_config(self, guild_id: int, category_id: int, support_role_id: int = None, 
                              log_channel_id: int = None, transcript_channel_id: int = None) -> bool:
        """Set ticket configuration for a guild"""
        async with self.async_session() as session:
            try:
                # Check if config already exists
                result = await session.execute(
                    select(TicketConfig).filter(TicketConfig.guild_id == guild_id)
                )
                config = result.scalar_one_or_none()
                
                if config:
                    # Update existing config
                    config.category_id = category_id
                    config.support_role_id = support_role_id
                    config.log_channel_id = log_channel_id
                    config.transcript_channel_id = transcript_channel_id
                    config.updated_at = datetime.utcnow()
                else:
                    # Create new config
                    config = TicketConfig(
                        guild_id=guild_id,
                        category_id=category_id,
                        support_role_id=support_role_id,
                        log_channel_id=log_channel_id,
                        transcript_channel_id=transcript_channel_id
                    )
                    session.add(config)
                
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error setting ticket config: {e}")
                await session.rollback()
                return False

    async def get_ticket_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get ticket configuration for a guild"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(TicketConfig).filter(TicketConfig.guild_id == guild_id)
                )
                config = result.scalar_one_or_none()
                return config.to_dict() if config else None
            except Exception as e:
                self.logger.error(f"Error getting ticket config: {e}")
                return None

    async def create_reaction_role(self, guild_id: int, message_id: int, channel_id: int, 
                                emoji: str, role_id: int) -> bool:
        """Create a reaction role"""
        async with self.async_session() as session:
            try:
                reaction_role = ReactionRole(
                    guild_id=guild_id,
                    message_id=message_id,
                    channel_id=channel_id,
                    emoji=emoji,
                    role_id=role_id
                )
                session.add(reaction_role)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error creating reaction role: {e}")
                await session.rollback()
                return False

    async def get_guild_reaction_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all reaction roles for a guild"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(ReactionRole).filter(ReactionRole.guild_id == guild_id)
                )
                reaction_roles = result.scalars().all()
                return [rr.to_dict() for rr in reaction_roles]
            except Exception as e:
                self.logger.error(f"Error getting guild reaction roles: {e}")
                return []

    async def delete_reaction_role(self, guild_id: int, message_id: int, emoji: str) -> bool:
        """Delete a reaction role"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(ReactionRole).filter(
                        ReactionRole.guild_id == guild_id,
                        ReactionRole.message_id == message_id,
                        ReactionRole.emoji == emoji
                    )
                )
                reaction_role = result.scalar_one_or_none()
                
                if reaction_role:
                    await session.delete(reaction_role)
                    await session.commit()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Error deleting reaction role: {e}")
                await session.rollback()
                return False

    async def create_auto_responder(self, guild_id: int, trigger: str, response: str, 
                                  enabled: bool = True, case_sensitive: bool = False, 
                                  regex: bool = False) -> bool:
        """Create an auto-responder"""
        async with self.async_session() as session:
            try:
                auto_responder = AutoResponder(
                    guild_id=guild_id,
                    trigger=trigger,
                    response=response,
                    enabled=enabled,
                    case_sensitive=case_sensitive,
                    regex=regex
                )
                session.add(auto_responder)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error creating auto-responder: {e}")
                await session.rollback()
                return False

    async def get_guild_auto_responders(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all auto-responders for a guild"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(AutoResponder).filter(
                        AutoResponder.guild_id == guild_id,
                        AutoResponder.enabled == True
                    )
                )
                auto_responders = result.scalars().all()
                return [ar.to_dict() for ar in auto_responders]
            except Exception as e:
                self.logger.error(f"Error getting guild auto-responders: {e}")
                return []

    async def create_custom_command(self, guild_id: int, command_name: str, response: str, 
                                  created_by: int) -> bool:
        """Create a custom command"""
        async with self.async_session() as session:
            try:
                custom_command = CustomCommand(
                    guild_id=guild_id,
                    command_name=command_name.lower(),
                    response=response,
                    created_by=created_by
                )
                session.add(custom_command)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error creating custom command: {e}")
                await session.rollback()
                return False

    async def get_custom_command(self, guild_id: int, command_name: str) -> Optional[Dict[str, Any]]:
        """Get a custom command"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(CustomCommand).filter(
                        CustomCommand.guild_id == guild_id,
                        CustomCommand.command_name == command_name.lower(),
                        CustomCommand.enabled == True
                    )
                )
                command = result.scalar_one_or_none()
                return command.to_dict() if command else None
            except Exception as e:
                self.logger.error(f"Error getting custom command: {e}")
                return None

    async def increment_custom_command_usage(self, command_id: int) -> bool:
        """Increment custom command usage count"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(CustomCommand).filter(CustomCommand.id == command_id)
                )
                command = result.scalar_one_or_none()
                
                if command:
                    command.uses += 1
                    await session.commit()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Error incrementing command usage: {e}")
                await session.rollback()
                return False

    async def get_guild_custom_commands(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all custom commands for a guild"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(CustomCommand).filter(
                        CustomCommand.guild_id == guild_id,
                        CustomCommand.enabled == True
                    )
                )
                commands = result.scalars().all()
                return [cmd.to_dict() for cmd in commands]
            except Exception as e:
                self.logger.error(f"Error getting guild custom commands: {e}")
                return []

    async def create_member_verification(self, guild_id: int, user_id: int, 
                                      verification_method: str = 'manual') -> bool:
        """Create a member verification record"""
        async with self.async_session() as session:
            try:
                verification = MemberVerification(
                    guild_id=guild_id,
                    user_id=user_id,
                    verification_method=verification_method
                )
                session.add(verification)
                await session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error creating member verification: {e}")
                await session.rollback()
                return False

    async def get_member_verification(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get member verification record"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(MemberVerification).filter(
                        MemberVerification.guild_id == guild_id,
                        MemberVerification.user_id == user_id
                    )
                )
                verification = result.scalar_one_or_none()
                return verification.to_dict() if verification else None
            except Exception as e:
                self.logger.error(f"Error getting member verification: {e}")
                return None

    async def verify_member(self, guild_id: int, user_id: int) -> bool:
        """Mark a member as verified"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(MemberVerification).filter(
                        MemberVerification.guild_id == guild_id,
                        MemberVerification.user_id == user_id
                    )
                )
                verification = result.scalar_one_or_none()
                
                if verification:
                    verification.verified = True
                    verification.verified_at = datetime.utcnow()
                    await session.commit()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Error verifying member: {e}")
                await session.rollback()
                return False


class StreamNotification(Base):
    """Stream notification model for tracking YouTube, Twitch, and Kick channels"""
    __tablename__ = 'stream_notifications'

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)  # Discord server ID
    discord_channel_id = Column(BigInteger, nullable=False)  # Discord channel to send notifications
    platform = Column(String(20), nullable=False)  # youtube, twitch, kick
    channel_id = Column(String(100), nullable=False)  # Platform channel ID/username
    added_by = Column(BigInteger, nullable=False)  # Discord user ID who added this
    last_video_id = Column(String(100))  # For YouTube - track last video ID
    last_stream_id = Column(String(100))  # For Twitch/Kick - track last stream ID
    is_live = Column(Boolean, default=False)  # Current live status
    enabled = Column(Boolean, default=True)  # Whether this notification is enabled
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'discord_channel_id': self.discord_channel_id,
            'platform': self.platform,
            'channel_id': self.channel_id,
            'added_by': self.added_by,
            'last_video_id': self.last_video_id,
            'last_stream_id': self.last_stream_id,
            'is_live': self.is_live,
            'enabled': self.enabled,
            'created_at': self.created_at
        }

class Ticket(Base):
    """Ticket model for support tickets"""
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)  # Discord channel for the ticket
    user_id = Column(BigInteger, nullable=False)  # User who created the ticket
    issue_type = Column(String(50), nullable=False)  # general, report, tech, appeal, etc.
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default='open')  # open, closed, pending
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'issue_type': self.issue_type,
            'subject': self.subject,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at,
            'closed_at': self.closed_at
        }

class TicketConfig(Base):
    """Ticket configuration model"""
    __tablename__ = 'ticket_configs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, unique=True, nullable=False)
    category_id = Column(BigInteger, nullable=False)  # Category for ticket channels
    support_role_id = Column(BigInteger)  # Role for support staff
    log_channel_id = Column(BigInteger)  # Channel for ticket logs
    transcript_channel_id = Column(BigInteger)  # Channel for ticket transcripts
    max_tickets_per_user = Column(Integer, default=3)  # Max tickets per user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'category_id': self.category_id,
            'support_role_id': self.support_role_id,
            'log_channel_id': self.log_channel_id,
            'transcript_channel_id': self.transcript_channel_id,
            'max_tickets_per_user': self.max_tickets_per_user
        }

class ReactionRole(Base):
    """Reaction role model"""
    __tablename__ = 'reaction_roles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)  # Message with reaction roles
    channel_id = Column(BigInteger, nullable=False)  # Channel containing the message
    emoji = Column(String(50), nullable=False)  # The emoji that triggers the role
    role_id = Column(BigInteger, nullable=False)  # The role to assign/remove
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'message_id': self.message_id,
            'channel_id': self.channel_id,
            'emoji': self.emoji,
            'role_id': self.role_id,
            'created_at': self.created_at
        }

class AutoResponder(Base):
    """Auto-responder model"""
    __tablename__ = 'auto_responders'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    trigger = Column(String(200), nullable=False)  # Word/phrase to trigger response
    response = Column(Text, nullable=False)  # Response to send
    enabled = Column(Boolean, default=True)
    case_sensitive = Column(Boolean, default=False)
    regex = Column(Boolean, default=False)  # Whether to treat trigger as regex
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'trigger': self.trigger,
            'response': self.response,
            'enabled': self.enabled,
            'case_sensitive': self.case_sensitive,
            'regex': self.regex,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class CustomCommand(Base):
    """Custom command model"""
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    command_name = Column(String(100), nullable=False)  # Command name without prefix
    response = Column(Text, nullable=False)  # Response to send
    created_by = Column(BigInteger, nullable=False)  # User who created the command
    uses = Column(Integer, default=0)  # Number of times command was used
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'command_name': self.command_name,
            'response': self.response,
            'created_by': self.created_by,
            'uses': self.uses,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class MemberVerification(Base):
    """Member verification model"""
    __tablename__ = 'member_verifications'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    verified = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    verification_method = Column(String(50))  # manual, captcha, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'user_id': self.user_id,
            'verified': self.verified,
            'joined_at': self.joined_at,
            'verified_at': self.verified_at,
            'verification_method': self.verification_method
        }