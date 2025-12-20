#!/bin/zsh

# CloneAI Auto-Start Installation Script
# This installs a LaunchAgent that starts CloneAI on login and keeps it running

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_FILE="com.cloneai.wakeup.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo "🚀 Installing CloneAI Auto-Start..."
echo ""

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Copy plist file to LaunchAgents
echo "📋 Copying launch agent configuration..."
cp "$SCRIPT_DIR/$PLIST_FILE" "$INSTALLED_PLIST"

# Update the path in the plist to use absolute path
echo "🔧 Configuring paths..."
sed -i '' "s|/Users/adarsh/Documents/GitHub/CloneAI|$SCRIPT_DIR|g" "$INSTALLED_PLIST"

# Make scripts executable
chmod +x "$SCRIPT_DIR/start-on-wake.sh"

# Unload if already loaded (ignore errors)
launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true

# Load the launch agent
echo "✅ Loading launch agent..."
launchctl load "$INSTALLED_PLIST"

echo ""
echo "✅ Installation complete!"
echo ""
echo "CloneAI will now:"
echo "  • Start automatically when you log in"
echo "  • Restart if it crashes"
echo "  • Run in the background"
echo ""
echo "Logs:"
echo "  • Auto-start: /tmp/cloneai-autostart.log"
echo "  • Backend: /tmp/cloneai-backend.log"
echo "  • UI: /tmp/cloneai-ui.log"
echo ""
echo "Commands:"
echo "  • Check status: launchctl list | grep cloneai"
echo "  • View logs: tail -f /tmp/cloneai-autostart.log"
echo "  • Disable: launchctl unload $INSTALLED_PLIST"
echo "  • Enable: launchctl load $INSTALLED_PLIST"
echo ""
echo "🎉 CloneAI is now configured to auto-start!"
