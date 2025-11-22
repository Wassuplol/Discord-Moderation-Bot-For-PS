# Changelog

All notable changes to OpenMod Discord Bot will be documented in this file.

## [1.1.1] - 2025-11-22

### Added
- **Stream Notifications**: 
  - YouTube video upload notifications (via RSS feeds)
  - Twitch streaming alerts (placeholder implementation)
  - Kick streaming alerts (placeholder implementation)
  - `stream add/remove/list/test` commands for managing stream notifications
  - Database model for tracking streamers and their notification settings

## [1.1.0] - 2025-11-22

### Added
- **Hybrid Commands**: All moderation commands now support both slash commands and traditional text commands for better user experience
- **Advanced Spam Detection**: 
  - Link spam detection and prevention
  - Duplicate message spam detection
  - Enhanced mention spam detection
- **Raid Protection**: 
  - Automatic raid detection based on rapid member joins
  - Configurable raid detection thresholds
- **New Moderation Commands**:
  - `lockdown` and `unlock` for emergency channel protection
  - `infraction` to view user's moderation history
  - `clean` to remove specific content types (links, images, bot messages, mentions)
- **Performance Optimizations**: Improved response times and memory usage
- **Enhanced Logging**: More detailed moderation logs with better tracking
- **Version Tracking**: Centralized version management in `core/version.py`

### Changed
- **Command System**: Converted all commands to hybrid commands (slash + text)
- **AutoMod System**: Enhanced with link spam, duplicate message, and raid detection
- **Error Handling**: Improved error messages and user feedback
- **Database Management**: Enhanced connection handling and optimization
- **Rate Limiting**: Better anti-abuse mechanisms

### Fixed
- Issues with command permissions and validation
- Memory leaks in spam detection systems
- Race conditions in moderation logging
- Performance issues with large servers
- Various edge cases in moderation commands

### Security
- Enhanced input validation across all commands
- Improved permission checks for all moderation actions
- Better rate limiting and anti-abuse mechanisms

## [1.0.0] - 2023-06-15

### Added
- Initial release of OpenMod Discord Bot
- Core moderation commands (warn, kick, ban, mute, etc.)
- Auto-moderation system with spam detection
- Basic logging and configuration
- Privacy-focused data handling
- MIT License for complete openness