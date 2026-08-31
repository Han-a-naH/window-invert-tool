$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$BuildVenv = Join-Path $ProjectRoot ".build-venv"
$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $BuildPython)) {
    Write-Host "Creating an isolated build environment..."
    python -m venv $BuildVenv
}

Write-Host "Installing the build tool..."
& $BuildPython -m pip install pyinstaller

Write-Host "Building WindowInvert.exe..."
& $BuildPython -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name WindowInvert window_invert.py

$OutputPath = Join-Path $ProjectRoot "dist\WindowInvert.exe"
if (-not (Test-Path -LiteralPath $OutputPath)) {
    throw "Build completed without creating $OutputPath"
}

Write-Host "Built: $OutputPath"
