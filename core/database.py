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