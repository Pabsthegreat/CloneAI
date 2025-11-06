#!/bin/zsh

# CloneAI Auto-Start Uninstallation Script

set -e

PLIST_FILE="com.cloneai.wakeup.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo "🗑️  Uninstalling CloneAI Auto-Start..."
echo ""

if [ ! -f "$INSTALLED_PLIST" ]; then
    echo "⚠️  Auto-start is not installed."
    exit 0
fi

# Unload the launch agent
echo "🔄 Unloading launch agent..."
launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true

# Remove the plist file
echo "🗑️  Removing configuration..."
rm -f "$INSTALLED_PLIST"

echo ""
echo "✅ Uninstallation complete!"
echo ""
echo "CloneAI will no longer start automatically."
echo "You can manually start it using:"
echo "  cd /Users/adarsh/Documents/GitHub/CloneAI"
echo "  ./start-on-wake.sh"
echo ""
