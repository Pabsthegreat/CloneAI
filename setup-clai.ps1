# CloneAI PowerShell Setup
# Add this to your PowerShell profile to use 'clai' from anywhere

# Get the CloneAI directory from script location
$CloneAIPath = Split-Path -Parent $PSCommandPath

# Create a function that calls the Python module
# Runs in CloneAI directory to ensure proper module loading
function clai {
    $originalLocation = Get-Location
    try {
        Set-Location $CloneAIPath
        python -m agent.cli @args
    }
    finally {
        Set-Location $originalLocation
    }
}

# Navigate to CloneAI directory
function clai-cd {
    Set-Location $CloneAIPath
}

Write-Host "✅ CloneAI commands loaded!" -ForegroundColor Green
Write-Host "   Use: clai hi" -ForegroundColor Cyan
Write-Host "   Use: clai chat 'your message'" -ForegroundColor Cyan
Write-Host "   Use: clai-cd (to navigate to CloneAI directory)" -ForegroundColor Cyan
