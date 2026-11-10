$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Miku.lnk'))
$shortcut.TargetPath = Join-Path $PSScriptRoot 'Launch Miku.bat'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,100"
$shortcut.Description = 'Open Miku, the local desktop assistant.'
$shortcut.Save()
$oldJarvis = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jarvis.lnk'
if (Test-Path -LiteralPath $oldJarvis) { Remove-Item -LiteralPath $oldJarvis }
Write-Output 'Created Miku shortcut on the Desktop.'
