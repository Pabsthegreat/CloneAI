# CloneAI Desktop

Cross-platform desktop application for CloneAI - Your AI-powered personal assistant.

## 🚀 Features

- **Natural Language Chat**: Interact with CloneAI using natural language
- **Email Management**: View and manage your emails
- **Calendar Integration**: View upcoming events
- **Workflow Management**: Create, view, and execute custom workflows
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **System Tray**: Run in the background with system tray integration
- **Global Shortcuts**: Quick access with `Cmd/Ctrl + Shift + A`

## 🏗️ Architecture

```
CloneAI Desktop
├── Electron Frontend (JavaScript)
│   ├── Chat Interface
│   ├── Email Viewer
│   ├── Calendar Viewer
│   └── Workflow Manager
│
└── Python Backend (FastAPI)
    ├── CloneAI Agent
    ├── Gmail API Integration
    ├── Google Calendar API
    └── Workflow Engine
```

## 📋 Prerequisites

- **Node.js** 18+ (for Electron)
- **Python** 3.10+ (for backend)
- **CloneAI** properly configured with Gmail/Calendar credentials

## 🛠️ Development Setup

### 1. Install Python Dependencies

```bash
cd /path/to/CloneAI
pip install -r requirements.txt
```

### 2. Install Electron Dependencies

```bash
cd electron-app
npm install
```

### 3. Start the App

**Option A: Start backend and frontend separately**

Terminal 1 (Python Backend):
```bash
cd /path/to/CloneAI
source .venv/bin/activate
python -m agent.server.api
```

Terminal 2 (Electron):
```bash
cd electron-app
npm start
```

**Option B: Start app in dev mode (auto-starts backend)**

```bash
cd electron-app
npm run dev
```

## 📦 Building for Distribution

### Build for Current Platform

```bash
cd electron-app
npm run build
```

### Build for Specific Platform

```bash
# macOS
npm run build:mac

# Windows
npm run build:win

# Linux
npm run build:linux
```

Distributable files will be in `electron-app/dist/`

## 🎮 Usage

### Global Shortcuts

- **`Cmd/Ctrl + Shift + A`**: Show/Hide CloneAI window

### Chat Commands

Examples:
```
"List my last 10 emails"
"Show my calendar for today"
"Search the web for best laptops 2024"
"Create a PDF from these images"
```

### Workflows

Custom workflows are stored in `~/.clai/workflows/custom/`

You can:
- Generate new workflows via natural language
- Edit workflow `.py` files directly
- Share workflows with others (copy `.py` files)

## 🔒 Security

- **Code Validation**: GPT-generated workflows are validated before execution
- **Sandboxed Execution**: Dangerous operations are blocked
- **Context Isolation**: Electron uses context isolation for security
- **Local-First**: All data stays on your machine

## 🐛 Troubleshooting

### Backend Won't Start

1. Check Python virtual environment is activated:
   ```bash
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. Verify dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

3. Test backend manually:
   ```bash
   python -m agent.server.api
   # Should see: "Uvicorn running on http://127.0.0.1:8765"
   ```

### Electron Won't Start

1. Reinstall dependencies:
   ```bash
   cd electron-app
   rm -rf node_modules package-lock.json
   npm install
   ```

2. Check Node.js version:
   ```bash
   node --version  # Should be 18+
   ```

### Connection Issues

1. Ensure backend is running on port 8765:
   ```bash
   curl http://127.0.0.1:8765/api/health
   ```

2. Check firewall settings (allow port 8765)

## 📁 Project Structure

```
electron-app/
├── src/
│   ├── main.js              # Electron main process
│   ├── preload.js           # Security bridge
│   └── renderer/
│       ├── index.html       # Frontend HTML
│       ├── styles.css       # UI styles
│       └── app.js           # Frontend logic
├── assets/
│   └── icon.png            # App icon
├── package.json            # npm dependencies
└── README.md              # This file

agent/server/
├── api.py                 # FastAPI backend server
└── __init__.py

agent/workflows/
└── validator.py           # Workflow security validator
```

## 🔧 Configuration

### Backend Port

Edit `agent/server/api.py`:
```python
def start_server(host: str = "127.0.0.1", port: int = 8765):
```

### Electron Window Size

Edit `electron-app/src/main.js`:
```javascript
mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    // ...
});
```

## 🚀 Deployment

### macOS

1. Build DMG:
   ```bash
   npm run build:mac
   ```

2. Distribute: `dist/CloneAI-1.0.0.dmg`

3. (Optional) Code sign for Gatekeeper:
   ```bash
   codesign --deep --force --verify --verbose --sign "Developer ID" dist/mac/CloneAI.app
   ```

### Windows

1. Build installer:
   ```bash
   npm run build:win
   ```

2. Distribute: `dist/CloneAI Setup 1.0.0.exe`

### Linux

1. Build AppImage:
   ```bash
   npm run build:linux
   ```

2. Distribute: `dist/CloneAI-1.0.0.AppImage`

## 📝 License

Same as CloneAI project

## 🙏 Credits

Built with:
- [Electron](https://www.electronjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- CloneAI Agent Framework
