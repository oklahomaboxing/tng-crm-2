$ErrorActionPreference = "Stop"

Write-Host "TNG Member Count Fix" -ForegroundColor Cyan

if (-not (Test-Path "backend\app\operations\dashboard.py")) {
    Write-Host "ERROR: Run this from the TNG CRM project root." -ForegroundColor Red
    Write-Host "Expected: backend\app\operations\dashboard.py"
    exit 1
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = "backups\member_count_fix_$stamp"
New-Item -ItemType Directory -Force -Path "$backup\backend\app\operations" | Out-Null

Copy-Item "backend\app\operations\dashboard.py" "$backup\backend\app\operations\dashboard.py"
Copy-Item "backend\app\operations\members.py" "$backup\backend\app\operations\members.py"

Copy-Item "$PSScriptRoot\patch\backend\app\operations\dashboard.py" "backend\app\operations\dashboard.py" -Force
Copy-Item "$PSScriptRoot\patch\backend\app\operations\members.py" "backend\app\operations\members.py" -Force

python -m compileall backend/app
if ($LASTEXITCODE -ne 0) {
    Write-Host "Compile failed. Restoring backup." -ForegroundColor Red
    Copy-Item "$backup\backend\app\operations\dashboard.py" "backend\app\operations\dashboard.py" -Force
    Copy-Item "$backup\backend\app\operations\members.py" "backend\app\operations\members.py" -Force
    exit 1
}

Write-Host "" 
Write-Host "SUCCESS: Dashboard and member filters corrected." -ForegroundColor Green
Write-Host "Backup saved to: $backup"
Write-Host "Next run: git add .; git commit -m 'Fix member count filters'; git push"
