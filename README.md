# OpenMod v2.0 - The Completely Free, Open-Source Discord Moderation Bot

**OpenMod** is a top-tier Discord moderation bot that provides ALL premium features other bots lock behind paywalls (Dyno, Carl-bot, MEE6, Wick, etc.), but 100% FREE FOREVER. No hidden costs, no premium tiers, no feature limitations.

## New in Version 2.0

### Essential Discord Moderation Features
- **Advanced Ticket System**: Complete ticket management with persistent views, multiple issue types, and transcript generation
- **Reaction Roles**: Persistent reaction role buttons with easy setup and management
- **Auto-Responder**: Customizable auto-responder with regex support and case sensitivity options
- **Custom Commands**: User-defined commands with usage tracking and analytics
- **Member Verification**: Enhanced verification system with button-based verification
- **Enhanced Database**: SQLAlchemy-based database with models for all new features
- **Improved Security**: Enhanced permission checks and input validation
- **Better Error Handling**: Comprehensive error handling across all modules

### Ticket System
- Create tickets with multiple issue types (General Support, Report User, Technical Issue, Appeal, Other)
- Persistent ticket creation buttons
- Ticket management commands for admins
- Transcript generation and logging
- User limits on ticket creation

### Reaction Roles
- Persistent reaction role buttons
- Easy setup with embed creation
- Support for multiple reaction roles per message
- Management commands for adding/removing reaction roles

### Auto-Responder
- Create custom responses to trigger phrases
- Support for regex patterns
- Case sensitivity options
- Enable/disable individual auto-responders

### Custom Commands
- Create custom commands with user-defined responses
- Usage tracking and analytics
- Command information and management
- Creator attribution

### Member Verification
- Button-based verification system
- Join tracking and verification status
- DM notifications for new members
- Verification status checking

### Version 1.1 Features (Carried Forward)
- **Hybrid Commands**: All commands now support both slash commands and traditional text commands
- **Advanced Spam Detection**: New link spam, duplicate message spam, and raid detection systems
- **Improved Auto-Moderation**: Enhanced filters with better accuracy and performance
- **Better Logging**: More detailed moderation logs with improved tracking
- **Performance Optimizations**: Improved response times and memory usage
- **Stream Notifications**: YouTube, Twitch, and Kick streaming notifications

### Version 1.1 Fixes (Carried Forward)
- Fixed issues with command permissions and validation
- Improved error handling and user feedback
- Enhanced database connection management
- Better rate limiting and anti-abuse mechanisms

## Features

### Stream Notifications
- YouTube video upload notifications (via RSS feeds)
- Twitch streaming alerts
- Kick streaming alerts
- Configure notification channels per streamer
- Commands to add/remove/list streamers

### Advanced Auto-Moderation System
- Spam detection with configurable thresholds
- Raid protection with automatic server lockdown capabilities
- Mention spam prevention
- Link filtering (whitelist/blacklist domains)
- File/image filtering
- Word filtering with regex support
- Anti-bot verification
- Voice channel spam protection
- Duplicate message detection
- Link spam prevention
- Raid detection and mitigation

### Comprehensive Logging System
- Message edit/delete logs
- Member join/leave tracking
- Role assignment/removal logs
- Channel modification logs
- Moderation action logs
- Bulk delete detection
- User activity tracking
- Command usage analytics

### Moderation Commands
- `warn`, `mute`, `kick`, `ban`, `unban`
- `purge` with multiple criteria
- `lockdown` and `unlock` for emergency protection
- `slowmode` with channel-specific settings
- `nick` and `role` management
- `infraction` to view user history
- `clean` to remove specific content types

### Stream Notification Commands
- `stream add <platform> <channel_id> [discord_channel]` - Add a streamer to monitor (Admin only)
- `stream remove <platform> <channel_id>` - Remove a streamer from monitoring (Admin only)
- `stream list` - List all monitored streamers (Admin only)
- `stream test <platform> <channel_id>` - Test sending a notification (Admin only)

### Customization & Automation
- Custom commands system
- Reaction roles
- Welcome/Goodbye messages
- Leveling system
- Server backup and restore
- Auto-moderation rule builder

### Utility & Community Features
- Poll system
- Giveaway system
- Ticket system
- Suggestion system
- Server analytics
- Role menus
- Voice channel management

## Privacy & Data Protection

- **STRICT DATA MINIMALISM**: Only collect data absolutely necessary for functionality
- **NO PERSONAL DATA**: Never store user emails, IPs, or private information
- **TEMPORARY STORAGE**: Message content logs only kept for 7 days maximum
- **USER CONTROL**: Commands for users to delete their data
- **DATA RETENTION POLICY**: Automatic cleanup of old data

## Installation

### Prerequisites
- Python 3.8+
- Discord Bot Token (from Discord Developer Portal)
- PostgreSQL or SQLite database

### Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/openmod.git
cd openmod
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the bot:
```bash
cp config.example.py config.py
# Edit config.py with your bot token and database settings
```

4. Run the bot:
```bash
python main.py
```

### Docker Setup

```bash
docker-compose up -d
```

## Self-Hosting

The bot is designed to be easily self-hostable on various platforms:
- Heroku
- Replit
- VPS
- Docker containers

## Contributing

Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Privacy Policy

For server owners: A template privacy policy is provided in `docs/privacy-policy-template.md`.