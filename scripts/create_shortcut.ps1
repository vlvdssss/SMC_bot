$target = Join-Path -Path $PSScriptRoot -ChildPath "..\dist\BAZA.exe"
$target = (Resolve-Path $target).ProviderPath
$desktop = [System.IO.Path]::Combine($env:USERPROFILE, 'Desktop')
$linkPath = [System.IO.Path]::Combine($desktop, 'BAZA.lnk')
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($linkPath)
$sc.TargetPath = $target
$sc.WorkingDirectory = Split-Path $target
$sc.Description = 'BAZA Trading Bot'
$sc.Save()
Write-Output "Shortcut created: $linkPath"