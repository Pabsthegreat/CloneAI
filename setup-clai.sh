#!/bin/bash
# CloneAI Shell Setup for Bash/Zsh
# Add this to your ~/.bashrc or ~/.zshrc to use 'clai' from anywhere

# Get the CloneAI directory automatically
if [ -n "${BASH_SOURCE[0]}" ]; then
    # Bash
    CLONEAI_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [ -n "${(%):-%x}" ]; then
    # Zsh
    CLONEAI_PATH="$(cd "$(dirname "${(%):-%x}")" && pwd)"
else
    # Fallback - assume current directory
    CLONEAI_PATH="$(pwd)"
fi

# Save original directory
ORIGINAL_DIR="$(pwd)"

# Change to CloneAI directory to run commands
clai() {
    (cd "$CLONEAI_PATH" && python3 -m agent.cli "$@")
}

# Navigate to CloneAI directory
clai-cd() {
    cd "$CLONEAI_PATH"
}

# Print success message with system detection
echo "✅ CloneAI commands loaded!"
echo "   Use: clai hi"
echo "   Use: clai chat 'your message'"
echo "   Use: clai-cd (to navigate to CloneAI directory)"
