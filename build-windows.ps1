$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python -m PyInstaller --clean --noconfirm --windowed --onedir --name RKTM-Admin --icon assets/admin.ico --add-data "WinSCP;WinSCP" --add-data "assets;assets" src/admin.py
if ($LASTEXITCODE -ne 0) { throw 'Admin build failed' }
python -m PyInstaller --clean --noconfirm --windowed --onedir --name RKTM-Uploader --icon assets/upload.ico --add-data "WinSCP;WinSCP" --add-data "assets;assets" src/employee.py
if ($LASTEXITCODE -ne 0) { throw 'Uploader build failed' }
if (-not (Test-Path 'dist/RKTM-Admin/RKTM-Admin.exe')) {throw 'Missing admin binary'}
if (-not (Test-Path 'dist/RKTM-Uploader/RKTM-Uploader.exe')) {throw 'Missing uploader binary'}
Write-Host 'Windows executables built.'
