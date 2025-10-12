# CloneAI Scheduler Auto-Start
# Add this to your PowerShell profile to auto-start the scheduler

$scriptPath = "C:\Users\adars\OneDrive\Documents\CloneAI"
$schedulerScript = Join-Path $scriptPath "start-scheduler.ps1"

# Check if scheduler job exists
$existingJob = Get-Job -Name "CloneAI-Scheduler" -ErrorAction SilentlyContinue

if (-not $existingJob) {
    # Start the scheduler silently
    & $schedulerScript
}
