# Create Windows Task Scheduler entry for CloneAI
# This will start the scheduler automatically when Windows boots

$taskName = "CloneAI-Scheduler"
$scriptPath = "C:\Users\adars\OneDrive\Documents\CloneAI\start-scheduler.ps1"

Write-Host ""
Write-Host "🔧 Creating Windows Task Scheduler entry..." -ForegroundColor Cyan
Write-Host ""

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "⚠️  Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Create the trigger (at logon)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Create the settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "CloneAI Task Scheduler - Runs scheduled tasks" -RunLevel Highest

Write-Host "✅ Windows Task created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The scheduler will now start automatically when you log in to Windows." -ForegroundColor Gray
Write-Host ""
Write-Host "To manage the task:" -ForegroundColor Cyan
Write-Host "  1. Open 'Task Scheduler' from Windows Start menu" -ForegroundColor White
Write-Host "  2. Look for '$taskName' in the task list" -ForegroundColor White
Write-Host ""
Write-Host "Or use PowerShell commands:" -ForegroundColor Cyan
Write-Host "  View task:    Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host "  Start now:    Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host "  Disable task: Disable-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host "  Remove task:  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor White
Write-Host ""
