#!/usr/bin/env python3
"""
CloneAI Documentation Server
Serves the documentation website locally for testing
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Configuration
PORT = 8000
DOCS_DIR = Path(__file__).parent

class DocumentationHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for documentation files"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)
    
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Colorized logging
        if args[1] == '200':
            print(f"\033[92m✓\033[0m {args[0]} - {args[1]}")
        elif args[1] == '304':
            print(f"\033[93m↻\033[0m {args[0]} - {args[1]} (cached)")
        else:
            print(f"\033[91m✗\033[0m {args[0]} - {args[1]}")

def main():
    """Start the documentation server"""
    os.chdir(DOCS_DIR)
    
    try:
        with socketserver.TCPServer(("", PORT), DocumentationHandler) as httpd:
            print("\n" + "="*60)
            print("📚 CloneAI Documentation Server")
            print("="*60)
            print(f"\n🌐 Server running at: \033[1;36mhttp://localhost:{PORT}\033[0m")
            print(f"📂 Serving from: {DOCS_DIR}")
            print(f"\n💡 Press Ctrl+C to stop the server")
            print("\n" + "="*60 + "\n")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48 or e.errno == 98:  # Address already in use
            print(f"\n❌ Error: Port {PORT} is already in use.")
            print(f"💡 Try: lsof -ti:{PORT} | xargs kill  (to free the port)")
            sys.exit(1)
        else:
            raise

if __name__ == "__main__":
    main()
