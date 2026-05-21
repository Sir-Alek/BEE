# Compila ELIA_Setup.iss y copia readme.txt junto al instalador (carpeta ELIA\).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    throw "No se encontró ISCC.exe. Instala Inno Setup 6 o ajusta la ruta en scripts/build_installer.ps1"
}

& $Iscc "ELIA_Setup.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ReadmeSrc = Join-Path $Root "readme.txt"
$ReadmeDst = Join-Path $Root "ELIA\readme.txt"
if (Test-Path $ReadmeSrc) {
    New-Item -ItemType Directory -Force -Path (Split-Path $ReadmeDst) | Out-Null
    Copy-Item $ReadmeSrc $ReadmeDst -Force
    Write-Host "OK readme.txt -> ELIA\readme.txt"
}

Write-Host "Instalador listo en ELIA\ELIA_Setup.exe"
