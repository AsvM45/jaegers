param([switch]$Offline)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Force .runtime | Out-Null
    $uvExe = Join-Path $projectRoot '.runtime/uv/uv.exe'
    if (-not (Test-Path -LiteralPath $uvExe)) {
        if ($Offline) { throw 'uv missing; first setup requires network access' }
        curl.exe -fL --max-time 120 https://github.com/astral-sh/uv/releases/download/0.13.7/uv-x86_64-pc-windows-msvc.zip -o .runtime/uv.zip
        if ($LASTEXITCODE -ne 0) { throw 'uv download failed' }
        Expand-Archive -LiteralPath .runtime/uv.zip -DestinationPath .runtime/uv
    }
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot '.runtime/python'
    $env:UV_CACHE_DIR = Join-Path $projectRoot '.runtime/cache'
    $uvFlags = @()
    if ($Offline) { $uvFlags += '--offline' }
    & $uvExe @uvFlags python install 3.13.18 --no-bin --no-registry
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.13.18 provisioning failed' }
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        & $uvExe @uvFlags venv .venv --python 3.13.18
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
    }
    & .venv/Scripts/python.exe -c 'import sys; assert sys.version_info[:3] == (3,13,18), sys.version; print(sys.version)'
    if ($LASTEXITCODE -ne 0) { throw 'Existing venv uses a different Python; preserve it and choose a fresh environment' }
    & $uvExe @uvFlags pip install --python .venv/Scripts/python.exe -r requirements-research.txt
    if ($LASTEXITCODE -ne 0) { throw 'Pinned research dependency install failed' }
} finally {
    Pop-Location
}
