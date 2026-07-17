# Post-flash Bullseye: mount boot, SSH, keys, hardware from old Stretch Pi
$ErrorActionPreference = 'Stop'
$DiskNumber = 1
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

$part = Get-Partition -DiskNumber $DiskNumber -PartitionNumber 1
$boot = $null
if ($part.DriveLetter) {
    $boot = "$($part.DriveLetter):\"
} else {
    foreach ($c in @('I','J','K','L','M','N','O','P')) {
        if (-not (Get-Volume -DriveLetter $c -ErrorAction SilentlyContinue)) {
            Set-Partition -DiskNumber $DiskNumber -PartitionNumber 1 -NewDriveLetter $c
            $boot = "${c}:\"
            break
        }
    }
}

if (-not $boot -or -not (Test-Path (Join-Path $boot 'config.txt'))) {
    Write-Error "Boot partition not found or not Raspberry Pi OS (no config.txt in $boot)"
}

Write-Host "Boot: $boot"
Get-ChildItem $boot | Select-Object -First 6 Name

# SSH on first boot (user pi — change default OS password immediately)
New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null

# SSH public key — copied to pi@ on first boot (Bullseye headless)
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii

# Hardware + display settings migrated from Stretch Pi (2026-07-06)
$cfg = Join-Path $boot 'config.txt'
$marker = '# --- TempMonitor (migrated from Stretch Pi) ---'
$content = Get-Content $cfg -Raw
if ($content -notmatch [regex]::Escape($marker)) {
    $append = @"

$marker
# Interfaces (was active on Stretch)
dtparam=i2c_arm=on
dtparam=spi=on
dtparam=audio=on
enable_uart=1
dtoverlay=pi3-miniuart-bt

# Display: HDMI Eizo primary, 7" DSI off (ignore_lcd=1)
ignore_lcd=1
lcd_rotate=2
disable_overscan=0

# Legacy framebuffer path for Kivy (no vc4-kms-v3d on Pi3 for now)
# dtoverlay=vc4-kms-v3d
gpu_mem=128
"@
    Add-Content -Path $cfg -Value $append -Encoding ascii
}

Write-Host 'Done: ssh, authorized_keys, config.txt updated'
Get-Content $cfg -Tail 18
