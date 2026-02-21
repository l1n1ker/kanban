$ErrorActionPreference = "Stop"

$dbPath = Join-Path $PSScriptRoot "..\\kanban.db"
$dbPath = (Resolve-Path $dbPath).Path
$backupDir = Join-Path $PSScriptRoot "..\\backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $backupDir ("kanban_{0}.db" -f $stamp)
Copy-Item -Path $dbPath -Destination $backupPath -Force
Write-Output ("Backup created: {0}" -f $backupPath)
