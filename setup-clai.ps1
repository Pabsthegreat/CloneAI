# CloneAI PowerShell Setup
# Add this to your PowerShell profile to use 'clai' from anywhere

# Get the CloneAI directory
$CloneAIPath = "C:\Users\adars\OneDrive\Documents\CloneAI"

# Create a function that calls the Python module
function clai {
    python -m agent.cli @args
}

# Optional: Set the working directory for the function
function clai-cd {
    Set-Location $CloneAIPath
}

Write-Host "✅ CloneAI commands loaded!" -ForegroundColor Green
Write-Host "   Use: clai hi" -ForegroundColor Cyan
Write-Host "   Use: clai chat 'your message'" -ForegroundColor Cyan
Write-Host "   Use: clai-cd (to navigate to CloneAI directory)" -ForegroundColor Cyan
