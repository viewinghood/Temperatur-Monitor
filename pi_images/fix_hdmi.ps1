$ErrorActionPreference = 'Stop'
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'
$Mode = if ($args[0] -eq 'eizo') { 'hdmi-eizo' } else { 'hdmi-safe' }

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

$boot = $null
foreach ($c in @('I','J','K','L','M','D')) {
    if (Test-Path "${c}:\config.txt") { $boot = "${c}:\"; break }
}
if (-not $boot) { Write-Error 'SD not found' }

Copy-Item (Join-Path $boot 'config.txt') (Join-Path $boot 'config.txt.bak-blink') -Force
Copy-Item "C:\Users\ritchie\temp_monitor\pi_images\config.txt.$Mode" (Join-Path $boot 'config.txt') -Force
$cmd = 'console=serial0,115200 console=tty1 root=PARTUUID=4e50d779-02 rootfstype=ext4 fsck.repair=yes rootwait systemd.unit=multi-user.target logo.nologo'
Set-Content -Path (Join-Path $boot 'cmdline.txt') -Value $cmd -NoNewline -Encoding ascii
New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii
Write-Host "Applied config.txt.$Mode on $boot"
Get-Content (Join-Path $boot 'config.txt')
