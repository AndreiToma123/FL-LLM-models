<#
  Run one experiment for one model, start to finish, and keep the PC awake while it runs.

    .\run-experiment.ps1 qwen25coder            # 100 bugs, main baseline
    .\run-experiment.ps1 llama31
    .\run-experiment.ps1 qwen35 -N 10           # quick 10-bug try first (this model may be slow)
    .\run-experiment.ps1 llama31 -Push          # also commit and push the finished reports to GitHub

  Easiest: use  .\run-experiment.cmd qwen25coder  (same thing, works even when PowerShell blocks scripts)
  If it stops (sleep, Ctrl+C, crash), run the same command again: finished bugs are skipped.
  Model names: see configs\models.json, or run:  docker compose run --rm soapfl python -m fl_tools models
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Model,
    [int]$N = 100,
    [int]$Jobs = 2,
    [switch]$Push
)

Set-Location $PSScriptRoot

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Desktop is not running. Start it, wait until it says 'running', and try again." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path ".env")) {
    Write-Host "No .env file. Run:  copy configs\ollama.env .env   and try again." -ForegroundColor Red
    exit 1
}

# keep Windows from going to sleep while this script runs (released automatically when it ends)
Add-Type -Namespace Win -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[void][Win.Power]::SetThreadExecutionState([uint32]2147483649)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED (0x80000001)

docker compose run --rm soapfl python -m fl_tools experiment $Model --n $N --jobs $Jobs
$code = $LASTEXITCODE

[void][Win.Power]::SetThreadExecutionState([uint32]2147483648)   # back to normal (0x80000000)

if ($code -ne 0) {
    Write-Host "`nThe experiment did not finish (exit code $code). Read the messages above, fix the cause, and run the same command again to resume." -ForegroundColor Yellow
    exit $code
}

$report = "reports\run$N-$Model"
Write-Host "`nFinished. Open $report\summary.md and $report\funnel.md" -ForegroundColor Green
if ($Push) {
    git add reports
    git commit -m "Add results: $Model, $N bugs"
    git push
}
