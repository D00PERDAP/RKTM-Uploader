param(
 [string]$Installer = ""
)
$ErrorActionPreference = 'Stop'
if (-not $env:RKTM_SIGNING_PFX_B64 -or -not $env:RKTM_SIGNING_PFX_PASSWORD) {
 throw 'Code-signing certificate or password is missing. Signed release is blocked.'
}
$signTool=(Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if (-not $signTool) {
 $signTool=Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
  Where-Object {$_.FullName -match '\\x64\\'} | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $signTool) {throw 'signtool.exe not found'}
$temp=Join-Path $env:RUNNER_TEMP 'rktm-signing.pfx'
try {
 [IO.File]::WriteAllBytes($temp,[Convert]::FromBase64String($env:RKTM_SIGNING_PFX_B64))
 $targets=@('dist/RKTM-Uploader/RKTM-Uploader.exe')
 if (-not $Installer) { foreach($target in $targets) {
  & $signTool sign /fd SHA256 /f $temp /p $env:RKTM_SIGNING_PFX_PASSWORD /tr http://timestamp.digicert.com /td SHA256 $target
  if ($LASTEXITCODE -ne 0) {throw "Signing failed for $target"}
  & $signTool verify /pa /v $target
  if ($LASTEXITCODE -ne 0) {throw "Signature verification failed for $target"}
 }
 }
 if ($Installer) {
  & $signTool sign /fd SHA256 /f $temp /p $env:RKTM_SIGNING_PFX_PASSWORD /tr http://timestamp.digicert.com /td SHA256 $Installer
  if ($LASTEXITCODE -ne 0) {throw 'Installer signing failed'}
  & $signTool verify /pa /v $Installer
  if ($LASTEXITCODE -ne 0) {throw 'Installer verification failed'}
 }
} finally {
 Remove-Item $temp -Force -ErrorAction SilentlyContinue
}
