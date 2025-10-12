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

# Change to CloneAI directory to run commands with auto-venv activation
clai() {
    local venv_python="$CLONEAI_PATH/.venv/bin/python3"
    
    # Check if venv exists and use its Python directly
    if [ -f "$venv_python" ]; then
        # Use venv Python (has all dependencies including document utilities)
        (cd "$CLONEAI_PATH" && "$venv_python" -m agent.cli "$@")
    else
        # No venv, use system Python (email/calendar features only)
        (cd "$CLONEAI_PATH" && python3 -m agent.cli "$@")
    fi
}

# Navigate to CloneAI directory
clai-cd() {
    cd "$CLONEAI_PATH"
}

# Print success message
echo "✅ CloneAI commands loaded!"
echo "   Use: clai hi"
echo "   Use: clai chat 'your message'"
echo "   Use: clai-cd (to navigate to CloneAI directory)"
