# Boot to rescue shell + force fsck — fix dbus/ssh after broken first boots
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

# Keep working hdmi config
Copy-Item 'C:\Users\ritchie\temp_monitor\pi_images\config.txt.hdmi-safe' (Join-Path $boot 'config.txt') -Force

# Rescue boot: fsck + repair mode (login as root possible)
$cmd = 'console=serial0,115200 console=tty1 root=PARTUUID=4e50d779-02 rootfstype=ext4 fsck.mode=force fsck.repair=yes rootwait systemd.unit=rescue.target logo.nologo'
Set-Content -Path (Join-Path $boot 'cmdline.txt') -Value $cmd -NoNewline -Encoding ascii
New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii
Write-Host "Rescue boot on $boot"
Write-Host $cmd
