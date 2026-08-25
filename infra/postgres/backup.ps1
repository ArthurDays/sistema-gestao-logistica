[CmdletBinding()]
param(
    [Parameter()]
    [string]$BackupDirectory = (Join-Path $PSScriptRoot 'backups'),

    [Parameter()]
    [ValidateRange(1, 365)]
    [int]$RetentionDays = 7
)

$ErrorActionPreference = 'Stop'
$databaseUrl = $env:DATABASE_URL
if (-not $databaseUrl) {
    throw 'DATABASE_URL deve ser fornecida por variável protegida.'
}
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    throw 'pg_dump não está disponível no PATH.'
}

New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$backupPath = Join-Path $BackupDirectory "logistica-$timestamp.dump"

& pg_dump --dbname=$databaseUrl --format=custom --no-owner --no-privileges --file=$backupPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $backupPath)) {
    throw 'pg_dump falhou; nenhum backup foi aceito.'
}

$file = Get-Item -LiteralPath $backupPath
if ($file.Length -eq 0) {
    Remove-Item -LiteralPath $backupPath -Force
    throw 'O backup gerado está vazio.'
}

$hash = Get-FileHash -LiteralPath $backupPath -Algorithm SHA256
Set-Content -LiteralPath "$backupPath.sha256" -Value "$($hash.Hash)  $($file.Name)" -Encoding ascii

$cutoff = (Get-Date).ToUniversalTime().AddDays(-$RetentionDays)
Get-ChildItem -LiteralPath $BackupDirectory -File -Filter 'logistica-*.dump*' |
    Where-Object { $_.LastWriteTimeUtc -lt $cutoff } |
    Remove-Item -Force

Write-Output "Backup validado: $($file.Name) ($($file.Length) bytes), SHA-256 $($hash.Hash)"
