const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * After-pack script for electron-builder
 * Creates a portable Python environment in the packaged app
 */
module.exports = async function(context) {
    console.log('\n🐍 Setting up Python environment for packaged app...\n');
    
    const { appOutDir, electronPlatformName, arch } = context;
    const appName = context.packager.appInfo.productFilename;
    
    let resourcesPath;
    if (electronPlatformName === 'darwin') {
        resourcesPath = path.join(appOutDir, `${appName}.app`, 'Contents', 'Resources');
    } else if (electronPlatformName === 'win32') {
        resourcesPath = path.join(appOutDir, 'resources');
    } else {
        resourcesPath = path.join(appOutDir, 'resources');
    }
    
    console.log(`Platform: ${electronPlatformName}`);
    console.log(`Architecture: ${arch}`);
    console.log(`Resources path: ${resourcesPath}\n`);
    
    // Create setup script for first run
    const setupScript = `#!/bin/bash

# CloneAI First-Run Setup
# Creates Python virtual environment on first launch

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Setting up Python environment (first run)..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS"
    echo "✅ Python environment ready!"
else
    echo "✅ Python environment already configured"
fi
`;

    if (electronPlatformName === 'darwin' || electronPlatformName === 'linux') {
        const setupScriptPath = path.join(resourcesPath, 'setup-python.sh');
        fs.writeFileSync(setupScriptPath, setupScript);
        fs.chmodSync(setupScriptPath, '755');
        console.log('✅ Created setup-python.sh');
    }
    
    console.log('\n✅ After-pack completed!\n');
};
