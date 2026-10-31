$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python tools/capture_ui.py
if ($LASTEXITCODE -ne 0) { throw 'UI rendering failed' }
python -m PyInstaller --clean --noconfirm --windowed --onedir --name RKTM-Uploader --version-file assets/version_info.txt --icon assets/upload.ico --add-data "WinSCP;WinSCP" --add-data "assets;assets" src/employee.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
if (-not (Test-Path 'dist/RKTM-Uploader/RKTM-Uploader.exe')) { throw 'Missing application binary' }
