# CloneAI Scheduler Background Service
# This script starts the CloneAI scheduler as a background job

$scriptPath = $PSScriptRoot
$venvPath = Join-Path $scriptPath ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "⏰ Starting CloneAI Scheduler in background..." -ForegroundColor Cyan
Write-Host ""

# Check if scheduler is already running
$existingJob = Get-Job -Name "CloneAI-Scheduler" -ErrorAction SilentlyContinue
if ($existingJob) {
    Write-Host "⚠️  Scheduler is already running (Job ID: $($existingJob.Id))" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To stop it, run:" -ForegroundColor Gray
    Write-Host "  Stop-Job -Name CloneAI-Scheduler" -ForegroundColor White
    Write-Host "  Remove-Job -Name CloneAI-Scheduler" -ForegroundColor White
    Write-Host ""
    exit 0
}

# Start the scheduler as a background job
$job = Start-Job -Name "CloneAI-Scheduler" -ScriptBlock {
    param($venvPath, $scriptPath)
    
    Set-Location $scriptPath
    & $venvPath -m agent.cli scheduler start
    
} -ArgumentList $venvPath, $scriptPath

Write-Host "✅ Scheduler started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Job Details:" -ForegroundColor Cyan
Write-Host "  Job ID: $($job.Id)" -ForegroundColor White
Write-Host "  Job Name: $($job.Name)" -ForegroundColor White
Write-Host "  Status: $($job.State)" -ForegroundColor Green
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  Check status:    Get-Job -Name CloneAI-Scheduler" -ForegroundColor White
Write-Host "  View output:     Receive-Job -Name CloneAI-Scheduler -Keep" -ForegroundColor White
Write-Host "  Stop scheduler:  Stop-Job -Name CloneAI-Scheduler" -ForegroundColor White
Write-Host "  Remove job:      Remove-Job -Name CloneAI-Scheduler -Force" -ForegroundColor White
Write-Host ""
Write-Host "💡 The scheduler will run your tasks at their scheduled times." -ForegroundColor Gray
Write-Host ""
