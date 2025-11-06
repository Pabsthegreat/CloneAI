# CloneAI Auto-Start Quick Guide

## Installation (One Command)

```bash
cd /Users/adarsh/Documents/GitHub/CloneAI
./install-autostart.sh
```

That's it! CloneAI will now start automatically.

## What Happens

After installation, CloneAI will automatically:
1. ✅ Start when you log in to your Mac
2. ✅ Start when your Mac wakes from sleep
3. ✅ Restart if it crashes
4. ✅ Run both backend (port 8765) and Electron UI

## Verify It's Working

**Check if it's running:**
```bash
launchctl list | grep cloneai
```

**View the logs:**
```bash
tail -f /tmp/cloneai-autostart.log
```

**Check backend:**
```bash
curl http://127.0.0.1:8765/api/health
```

## Uninstall

If you want to disable auto-start:

```bash
./uninstall-autostart.sh
```

## Troubleshooting

**Not starting?**
```bash
# Check logs
tail -50 /tmp/cloneai-autostart.log

# Try manual start
./start-on-wake.sh

# Reinstall
./uninstall-autostart.sh
./install-autostart.sh
```

**Want to restart it?**
```bash
launchctl unload ~/Library/LaunchAgents/com.cloneai.wakeup.plist
launchctl load ~/Library/LaunchAgents/com.cloneai.wakeup.plist
```

## More Info

See [AUTOSTART.md](AUTOSTART.md) for complete documentation.
