$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python make_icon.py
if ($LASTEXITCODE -ne 0) { throw "生成图标失败" }

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "TXT分类管理器" `
    --icon "$PSScriptRoot\assets\app.ico" `
    --distpath "$PSScriptRoot\dist" `
    --workpath "$PSScriptRoot\build" `
    --specpath "$PSScriptRoot" `
    app.py

if ($LASTEXITCODE -ne 0) { throw "打包失败" }
Write-Host "输出: $PSScriptRoot\dist\TXT分类管理器.exe"
