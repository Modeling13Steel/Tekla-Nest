<#
.SYNOPSIS
    Prepare a portable Python embeddable package with pythonnet pre-installed.
.DESCRIPTION
    Downloads the official Python embeddable package from python.org,
    bootstraps pip, installs pythonnet, and outputs a self-contained
    folder (build/python-embed/) ready to bundle with the installer.
.PARAMETER PythonVersion
    Python version to download (default: 3.12.7).
.PARAMETER OutputDir
    Destination folder (default: build/python-embed).
#>
param(
    [string]$PythonVersion = "3.11.9",
    [string]$OutputDir = "build\python-embed"
)

$ErrorActionPreference = "Stop"

$major, $minor, $patch = $PythonVersion -split '\.'
$tag = "$major$minor"
$zipName = "python-$PythonVersion-embed-amd64.zip"
$url = "https://www.python.org/ftp/python/$PythonVersion/$zipName"
$pipUrl = "https://bootstrap.pypa.io/get-pip.py"

# ── Download & extract ───────────────────────────────────────

if (Test-Path $OutputDir) { Remove-Item $OutputDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$zipPath = "$env:TEMP\$zipName"
Write-Host "Downloading Python $PythonVersion embeddable package..."
Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
Expand-Archive -Path $zipPath -DestinationPath $OutputDir -Force
Remove-Item $zipPath

# ── Enable site-packages (required for pip) ──────────────────

# The embeddable package ships a python3XX._pth that disables site-packages.
# We need to uncomment the "import site" line.
$pthFile = Join-Path $OutputDir "python$tag._pth"
if (Test-Path $pthFile) {
    $content = Get-Content $pthFile -Raw
    $content = $content -replace '#import site', 'import site'
    Set-Content $pthFile $content -NoNewline
    Write-Host "Enabled site-packages in $pthFile"
}

# ── Bootstrap pip ────────────────────────────────────────────

$python = Join-Path $OutputDir "python.exe"
$getPip = "$env:TEMP\get-pip.py"
Write-Host "Bootstrapping pip..."
Invoke-WebRequest -Uri $pipUrl -OutFile $getPip -UseBasicParsing
& $python $getPip --no-warn-script-location 2>&1 | Write-Host
Remove-Item $getPip

# ── Install pythonnet ────────────────────────────────────────

Write-Host "Installing pythonnet..."
& $python -m pip install pythonnet --no-warn-script-location 2>&1 | Write-Host

# ── Verify ───────────────────────────────────────────────────

Write-Host "Verifying pythonnet import..."
& $python -c "import clr; print('pythonnet OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Error "pythonnet verification failed!"
    exit 1
}

# ── Cleanup pip cache & unnecessary files ────────────────────

& $python -m pip cache purge 2>$null

$sizeKB = [math]::Round((Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1KB)
Write-Host ""
Write-Host "Done! Portable Python with pythonnet ready at: $OutputDir ($sizeKB KB)"
