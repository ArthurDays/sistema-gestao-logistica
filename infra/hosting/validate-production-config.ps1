[CmdletBinding()]
param(
    [Parameter()]
    [string]$Path = (Join-Path $PSScriptRoot 'production.env.example')
)

$ErrorActionPreference = 'Stop'
$sensitiveKeyPattern = '(?i)(secret|senha|password|token|database_url|dsn)$'
$placeholderPattern = '^<[^>]+>$'
$values = @{}
$errors = [System.Collections.Generic.List[string]]::new()

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Arquivo de configuração não encontrado: $Path"
}

foreach ($line in Get-Content -LiteralPath $Path -Encoding utf8) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) {
        continue
    }

    $key, $value = $trimmed -split '=', 2
    if (-not $value) {
        $errors.Add("$key deve possuir um valor.")
        continue
    }
    $values[$key.Trim()] = $value.Trim()
}

$required = 'FRONTEND_URL', 'BACKEND_URL', 'CORS_ORIGINS', 'GOOGLE_REDIRECT_URI'
foreach ($key in $required) {
    if (-not $values.ContainsKey($key)) {
        $errors.Add("Variável obrigatória ausente: $key")
    }
}

foreach ($key in 'FRONTEND_URL', 'BACKEND_URL', 'GOOGLE_REDIRECT_URI') {
    if (-not $values.ContainsKey($key)) {
        continue
    }
    $uri = $null
    if (-not [Uri]::TryCreate($values[$key], [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https') {
        $errors.Add("$key deve usar uma URL HTTPS absoluta.")
    }
}

if ($values.ContainsKey('CORS_ORIGINS')) {
    $origins = $values['CORS_ORIGINS'] -split ',' | ForEach-Object { $_.Trim() }
    if ($origins -contains '*') {
        $errors.Add('CORS_ORIGINS não pode permitir origem curinga em produção.')
    }
    foreach ($origin in $origins) {
        $uri = $null
        if (-not [Uri]::TryCreate($origin, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https') {
            $errors.Add("CORS_ORIGINS contém origem sem HTTPS: $origin")
        }
    }
}

if ($values.ContainsKey('BACKEND_URL') -and $values.ContainsKey('GOOGLE_REDIRECT_URI')) {
    $backend = [Uri]$values['BACKEND_URL']
    $redirect = [Uri]$values['GOOGLE_REDIRECT_URI']
    if ($backend.Host -ne $redirect.Host -or $redirect.AbsolutePath -ne '/api/v1/auth/google/callback') {
        $errors.Add('GOOGLE_REDIRECT_URI deve apontar para o callback OAuth do backend publicado.')
    }
}

foreach ($entry in $values.GetEnumerator()) {
    if ($entry.Key -match $sensitiveKeyPattern -and $entry.Value -notmatch $placeholderPattern) {
        $errors.Add("$($entry.Key) aparenta conter secret, senha, password ou token literal.")
    }
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    throw "Configuração de produção rejeitada com $($errors.Count) erro(s)."
}

Write-Output 'Configuração de produção válida: HTTPS, CORS e callback OAuth coerentes; nenhum segredo literal.'
