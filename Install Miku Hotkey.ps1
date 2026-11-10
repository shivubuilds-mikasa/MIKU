$ErrorActionPreference = 'Stop'
$rootPath = $PSScriptRoot
$startupPath = [Environment]::GetFolderPath('Startup')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $startupPath 'Miku Ctrl+J.lnk'))
$shortcut.TargetPath = Join-Path $rootPath '.venv\Scripts\pythonw.exe'
$shortcut.Arguments = '"' + (Join-Path $rootPath 'miku_hotkey.py') + '"'
$shortcut.WorkingDirectory = $rootPath
$shortcut.Description = 'Registers Ctrl+J to show or launch Miku for this Windows user.'
$shortcut.Save()
Write-Output 'Installed the per-user Ctrl+J listener in the Windows Startup folder.'
