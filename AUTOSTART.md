# CloneAI Auto-Start on Wake/Login

This feature automatically starts the CloneAI backend and Electron UI when your Mac wakes from sleep or when you log in.

## Installation

### Quick Install

```bash
cd /Users/adarsh/Documents/GitHub/CloneAI
./install-autostart.sh
```

This will:
- ✅ Configure a macOS LaunchAgent
- ✅ Start CloneAI automatically on login
- ✅ Restart CloneAI if it crashes
- ✅ Keep both backend and UI running in the background

## Usage

### After Installation

CloneAI will automatically start:
- ✅ When you log in to your Mac
- ✅ When your Mac wakes from sleep
- ✅ If the app crashes (auto-restart)

### Manual Control

**Check Status:**
```bash
launchctl list | grep cloneai
```

**View Logs:**
```bash
# Auto-start log
tail -f /tmp/cloneai-autostart.log

# Backend log
tail -f /tmp/cloneai-backend.log

# UI log
tail -f /tmp/cloneai-ui.log
```

**Temporarily Disable:**
```bash
launchctl unload ~/Library/LaunchAgents/com.cloneai.wakeup.plist
```

**Re-enable:**
```bash
launchctl load ~/Library/LaunchAgents/com.cloneai.wakeup.plist
```

**Start Manually:**
```bash
./start-on-wake.sh
```

### Uninstallation

To disable auto-start completely:

```bash
./uninstall-autostart.sh
```

## How It Works

### Architecture

```
macOS Login/Wake
      ↓
LaunchAgent (com.cloneai.wakeup.plist)
      ↓
start-on-wake.sh
      ↓
   ┌──────────────┬──────────────┐
   ↓              ↓              ↓
Backend      Wait 3s       Electron UI
(Python)                    (Node.js)
```

### Components

1. **com.cloneai.wakeup.plist** - LaunchAgent configuration
   - Installed in: `~/Library/LaunchAgents/`
   - Runs: `start-on-wake.sh` on login
   - Auto-restarts on failure

2. **start-on-wake.sh** - Startup script
   - Checks if processes already running
   - Starts Python backend (port 8765)
   - Waits 3 seconds
   - Starts Electron UI
   - Logs to `/tmp/cloneai-*.log`

3. **install-autostart.sh** - Installation script
   - Copies plist to LaunchAgents
   - Updates paths automatically
   - Loads the launch agent

4. **uninstall-autostart.sh** - Removal script
   - Unloads the launch agent
   - Removes plist file

### Logs

All logs are stored in `/tmp/`:

- **cloneai-autostart.log** - Auto-start events and status
- **cloneai-backend.log** - Python backend output
- **cloneai-ui.log** - Electron UI output
- **cloneai-wakeup.log** - LaunchAgent stdout
- **cloneai-wakeup-error.log** - LaunchAgent stderr

## Troubleshooting

### Check if installed

```bash
ls -la ~/Library/LaunchAgents/com.cloneai.wakeup.plist
```

### Check if running

```bash
launchctl list | grep cloneai
ps aux | grep "agent.server.api"
ps aux | grep electron
```

### View recent logs

```bash
tail -50 /tmp/cloneai-autostart.log
```

### Force restart

```bash
launchctl unload ~/Library/LaunchAgents/com.cloneai.wakeup.plist
launchctl load ~/Library/LaunchAgents/com.cloneai.wakeup.plist
```

### Complete reinstall

```bash
./uninstall-autostart.sh
./install-autostart.sh
```

## Security Notes

- The LaunchAgent runs with your user permissions (not root)
- Scripts only access your CloneAI directory
- Logs are stored in `/tmp/` (cleared on reboot)
- Backend runs on localhost only (127.0.0.1:8765)

## Customization

### Change startup behavior

Edit `start-on-wake.sh` to customize:
- Startup delay (default: 3 seconds)
- Log locations
- Additional startup commands

### Change when it runs

Edit `com.cloneai.wakeup.plist` for advanced options:
- `RunAtLoad` - Run on login (currently: true)
- `KeepAlive` - Restart on crash (currently: true)
- `StartInterval` - Run periodically (not set)

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.cloneai.wakeup.plist
launchctl load ~/Library/LaunchAgents/com.cloneai.wakeup.plist
```

## Support

If auto-start isn't working:

1. Check logs: `tail -50 /tmp/cloneai-autostart.log`
2. Verify installation: `ls -la ~/Library/LaunchAgents/com.cloneai.wakeup.plist`
3. Test manually: `./start-on-wake.sh`
4. Check permissions: `ls -l start-on-wake.sh` (should show `x` flag)
5. Reinstall: `./uninstall-autostart.sh && ./install-autostart.sh`
