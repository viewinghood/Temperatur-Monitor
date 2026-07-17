# Post-flash: mount boot partition and enable SSH + SPI for TempMonitor
$ErrorActionPreference = 'Stop'
$DiskNumber = 1
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'

$part = Get-Partition -DiskNumber $DiskNumber -PartitionNumber 1
if (-not $part.DriveLetter) {
    $letter = (Get-Volume | Where-Object { -not $_.DriveLetter -and $_.FileSystem -eq 'FAT32' -and $_.Size -lt 600MB } | Select-Object -First 1)
    # assign first free letter
    foreach ($c in 'J','K','L','M','N','O','P') {
        if (-not (Get-Volume -DriveLetter $c -ErrorAction SilentlyContinue)) {
            Set-Partition -DiskNumber $DiskNumber -PartitionNumber 1 -NewDriveLetter $c
            $boot = "${c}:\"
            break
        }
    }
} else {
    $boot = "$($part.DriveLetter):\"
}

if (-not $boot -or -not (Test-Path $boot)) {
    Write-Error "Boot partition not mounted"
}

Write-Host "Boot partition: $boot"
Get-ChildItem $boot | Select-Object -First 8 Name

# Enable SSH on first boot (Bullseye)
New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null

# SSH public key (copied to pi/.ssh on first boot)
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -NoNewline -Encoding ascii

# TempMonitor hardware: SPI + UART on Pi 3
$cfg = Join-Path $boot 'config.txt'
$append = @'

# --- TempMonitor (added by flash setup) ---
dtparam=spi=on
enable_uart=1
dtoverlay=pi3-miniuart-bt
'@
Add-Content -Path $cfg -Value $append -Encoding ascii

Write-Host 'Configured: ssh, authorized_keys, spi/uart in config.txt'
Get-Content $cfg -Tail 6
