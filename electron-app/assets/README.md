# CloneAI App Icons

Since we don't have custom icons yet, the build will use Electron's default icon.

## To add custom icons:

### macOS (.icns)
1. Create a 1024x1024 PNG icon
2. Use an online converter or iconutil:
   ```bash
   mkdir icon.iconset
   # Add various sizes (16x16, 32x32, 64x64, 128x128, 256x256, 512x512, 1024x1024)
   iconutil -c icns icon.iconset
   ```
3. Save as `electron-app/assets/icon.icns`

### Windows (.ico)
1. Create a 256x256 PNG icon
2. Use an online ICO converter
3. Save as `electron-app/assets/icon.ico`

### Linux (.png)
1. Create a 512x512 PNG icon
2. Save as `electron-app/assets/icon.png`

### DMG Background
1. Create a 540x400 PNG image for the DMG installer background
2. Save as `electron-app/assets/dmg-background.png`

## For now:
The build will work without custom icons - it will just use Electron's default.
