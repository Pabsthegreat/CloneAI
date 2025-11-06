# Building CloneAI Desktop App

This guide shows you how to build CloneAI into a distributable macOS application (.dmg).

## Prerequisites

1. **Node.js and npm** installed
2. **Python 3.10+** installed
3. **CloneAI backend** working (test with `python -m agent.server.api`)

## Quick Build (macOS)

```bash
cd /Users/adarsh/Documents/GitHub/CloneAI/electron-app

# Install dependencies (if not already done)
npm install

# Build DMG for macOS
npm run build:mac
```

The DMG will be created in: `electron-app/dist/CloneAI-1.0.0-{arch}.dmg`

Where `{arch}` is either `x64` (Intel) or `arm64` (Apple Silicon).

## Build Options

### Build for current architecture only:
```bash
npm run build:mac
```

### Build for specific architecture:
```bash
# Intel (x64)
npm run build:mac -- --x64

# Apple Silicon (arm64)
npm run build:mac -- --arm64

# Universal (both)
npm run build:mac -- --universal
```

### Just package (no installer):
```bash
npm run pack
```

This creates an app bundle without DMG/ZIP, useful for testing.

## What Gets Packaged

The built app includes:

✅ **Electron UI** - All frontend files (HTML, CSS, JS)
✅ **Python Backend** - All agent code and tools
✅ **Requirements** - requirements.txt for Python dependencies
✅ **Auto-Setup** - First-run script creates Python venv

**Note:** The `.venv` folder is NOT included in the build (too large). Instead, a setup script runs on first launch to create it.

## Build Output

After building, you'll find in `electron-app/dist/`:

- `CloneAI-1.0.0-arm64.dmg` - Apple Silicon installer
- `CloneAI-1.0.0-x64.dmg` - Intel installer
- `CloneAI-1.0.0-arm64-mac.zip` - Apple Silicon portable
- `CloneAI-1.0.0-x64-mac.zip` - Intel portable

## Install the Built App

1. **Open the DMG**: Double-click `CloneAI-1.0.0-{arch}.dmg`
2. **Drag to Applications**: Drag CloneAI icon to Applications folder
3. **First Launch**: The app will set up Python environment (takes 1-2 minutes)
4. **Use**: After setup, the app is ready to use!

## First Launch

On first launch, the app will:

1. ✅ Check for Python
2. ✅ Create virtual environment
3. ✅ Install Python dependencies
4. ✅ Start backend server
5. ✅ Show UI

You'll see progress in the app window or in logs.

## Testing the Build

Before distributing:

```bash
# Build the app
npm run build:mac

# Open the DMG
open dist/CloneAI-1.0.0-arm64.dmg

# Install to Applications
# (Drag the app icon to Applications in the DMG window)

# Launch from Applications
open /Applications/CloneAI.app
```

## Troubleshooting

### Build fails with icon error
- Icons are optional. If build fails due to missing icons, they'll use Electron defaults
- To add custom icons, see `assets/README.md`

### Build fails with "Command failed: python3"
- Make sure Python 3.10+ is installed: `python3 --version`
- The build doesn't require Python, but the app will need it to run

### DMG too large
- The DMG includes all Python code and dependencies
- Typical size: 50-100 MB (without venv)
- With venv included: 200-500 MB (not recommended)

### App won't open ("damaged or unverified")
This is normal for unsigned apps. To fix:

```bash
# Remove quarantine attribute
xattr -cr /Applications/CloneAI.app

# Or use System Preferences:
# System Preferences → Security & Privacy → Allow CloneAI
```

### Python setup fails on first launch
Check logs in:
- Console.app (search for "CloneAI")
- `~/Library/Logs/CloneAI/`

## Code Signing (Optional)

To distribute publicly, you should code sign:

```bash
# Requires Apple Developer account and certificate

# Add to package.json build.mac:
{
  "identity": "Your Name (TEAM_ID)",
  "hardenedRuntime": true,
  "entitlements": "entitlements.mac.plist"
}

# Then build:
npm run build:mac
```

## Notarization (Optional)

For distribution outside App Store:

```bash
# After building and signing:
xcrun notarytool submit dist/CloneAI-1.0.0-arm64.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# Staple the notarization:
xcrun stapler staple dist/CloneAI-1.0.0-arm64.dmg
```

## Build Scripts

Available npm scripts:

- `npm run build` - Build for current platform
- `npm run build:mac` - Build macOS DMG
- `npm run build:win` - Build Windows installer
- `npm run build:linux` - Build Linux AppImage/deb
- `npm run pack` - Package without installer
- `npm run dist` - Build all formats

## Performance Tips

### Faster builds:
```bash
# Skip compression
npm run build:mac -- --config.compression=store

# Skip source maps
npm run build:mac -- --config.removePackageScripts=true
```

### Smaller app size:
- Don't include `.venv` (already excluded)
- Exclude test files (already excluded)
- Compress with maximum: `"compression": "maximum"` in package.json

## Distribution

### For testing (unSigned):
1. Build: `npm run build:mac`
2. Share the DMG file
3. Users install and allow in Security settings

### For public (signed & notarized):
1. Get Apple Developer certificate
2. Configure code signing
3. Build and sign
4. Notarize with Apple
5. Distribute the notarized DMG

## Next Steps

After building:
1. ✅ Test the DMG installation
2. ✅ Test first launch and Python setup
3. ✅ Test all features (email, calendar, chat)
4. ✅ Check app performance
5. ✅ Consider code signing for wider distribution

## Support

If build issues occur:
1. Check `electron-builder` logs
2. Verify Node.js version: `node --version` (should be 16+)
3. Clear cache: `rm -rf node_modules dist && npm install`
4. Check GitHub issues: https://github.com/electron-userland/electron-builder

## Resources

- [electron-builder docs](https://www.electron.build/)
- [macOS Distribution](https://www.electron.build/configuration/mac)
- [Code Signing Guide](https://www.electron.build/code-signing)
