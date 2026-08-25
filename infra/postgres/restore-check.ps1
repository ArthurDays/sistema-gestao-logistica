[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BackupPath,

    [Parameter()]
    [string]$RestoreDatabaseUrl = $env:RESTORE_DATABASE_URL
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $BackupPath -PathType Leaf)) {
    throw "Backup não encontrado: $BackupPath"
}
if (-not $RestoreDatabaseUrl) {
    throw 'RESTORE_DATABASE_URL deve apontar para um banco isolado e descartável.'
}
if ($env:DATABASE_URL -and $RestoreDatabaseUrl -eq $env:DATABASE_URL) {
    throw 'A restauração nunca pode usar a URL do banco de origem.'
}
if (-not (Get-Command pg_restore -ErrorAction SilentlyContinue)) {
    throw 'pg_restore não está disponível no PATH.'
}

$expectedHashPath = "$BackupPath.sha256"
if (Test-Path -LiteralPath $expectedHashPath) {
    $expectedHash = ((Get-Content -LiteralPath $expectedHashPath -Raw).Trim() -split '\s+')[0]
    $actualHash = (Get-FileHash -LiteralPath $BackupPath -Algorithm SHA256).Hash
    if ($expectedHash -ne $actualHash) {
        throw 'Checksum SHA-256 do backup não confere.'
    }
}

# O destino deve ser temporário/isolado; --clean atua somente nesse banco descartável.
& pg_restore --dbname=$RestoreDatabaseUrl --clean --if-exists --no-owner --no-privileges $BackupPath
if ($LASTEXITCODE -ne 0) {
    throw 'A restauração isolada falhou.'
}

Write-Output 'Restauração concluída no banco isolado; a origem não foi alterada.'
