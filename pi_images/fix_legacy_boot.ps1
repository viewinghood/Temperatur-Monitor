# Legacy boot — disable ALL vc4/KMS, match Stretch display stack
$ErrorActionPreference = 'Stop'
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

$boot = $null
foreach ($c in @('I','J','K','L','M','D')) {
    if (Test-Path "${c}:\config.txt") { $boot = "${c}:\"; break }
}
if (-not $boot) { Write-Error 'SD not found' }

Write-Host "LEGACY config on $boot"
Copy-Item (Join-Path $boot 'config.txt') (Join-Path $boot 'config.txt.bak-fkms') -Force
Copy-Item 'C:\Users\ritchie\temp_monitor\pi_images\config.txt.legacy' (Join-Path $boot 'config.txt') -Force

# cmdline: no splash/plymouth (flicker), console boot, no GUI
$cmd = 'console=serial0,115200 console=tty1 root=PARTUUID=4e50d779-02 rootfstype=ext4 fsck.repair=yes rootwait systemd.unit=multi-user.target logo.nologo'
Set-Content -Path (Join-Path $boot 'cmdline.txt') -Value $cmd -NoNewline -Encoding ascii

New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii

Write-Host 'Done — NO vc4/KMS, start_x=0, ignore_lcd=1, no splash'
Get-Content (Join-Path $boot 'config.txt')
