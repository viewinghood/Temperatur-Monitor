# Post-flash setup: Bullseye Lite — HDMI 1280x1024, SPI, SSH key
$ErrorActionPreference = 'Stop'
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

# Find boot partition (config.txt on FAT32)
$boot = $null
foreach ($c in @('D','E','F','G','H','I','J','K','L','M')) {
    if (Test-Path "${c}:\config.txt") { $boot = "${c}:\"; break }
}
if (-not $boot) {
    foreach ($p in Get-Partition | Where-Object { $_.DriveLetter -and $_.Size -lt 600MB }) {
        $try = "$($p.DriveLetter):\"
        if (Test-Path "$try\config.txt") { $boot = $try; break }
    }
}
if (-not $boot) {
    # Assign letter to unlettered FAT32 on removable disk
    $fat = Get-Partition | Where-Object { -not $_.DriveLetter -and $_.Type -match 'FAT' -and $_.Size -lt 600MB } | Select-Object -First 1
    if ($fat) {
        foreach ($c in @('I','J','K')) {
            if (-not (Get-Volume -DriveLetter $c -ErrorAction SilentlyContinue)) {
                Set-Partition -DiskNumber $fat.DiskNumber -PartitionNumber $fat.PartitionNumber -NewDriveLetter $c
                $boot = "${c}:\"
                break
            }
        }
    }
}
if (-not $boot -or -not (Test-Path (Join-Path $boot 'config.txt'))) {
    Write-Error 'SD boot partition not found — re-insert SD card in reader'
}

Write-Host "Post-flash setup on $boot"

Copy-Item 'C:\Users\ritchie\temp_monitor\pi_images\config.txt.lite-final' (Join-Path $boot 'config.txt') -Force

# Keep PARTUUID from Etcher image; clean cmdline for console boot
$old = (Get-Content (Join-Path $boot 'cmdline.txt') -Raw).Trim()
if ($old -match 'root=PARTUUID=[0-9a-f-]+') {
    $rootPart = $Matches[0]
} elseif ($old -match 'root=PARTUUID=\S+') {
    $rootPart = ($old -split '\s+' | Where-Object { $_ -like 'root=PARTUUID=*' })[0]
} else {
    $rootPart = 'root=PARTUUID=00000000-02'
}
$newCmd = "console=serial0,115200 console=tty1 $rootPart rootfstype=ext4 fsck.repair=yes rootwait systemd.unit=multi-user.target logo.nologo"
Set-Content -Path (Join-Path $boot 'cmdline.txt') -Value $newCmd -NoNewline -Encoding ascii

New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii

Write-Host '=== DONE ==='
Write-Host "Boot: $boot"
Write-Host 'cmdline:' (Get-Content (Join-Path $boot 'cmdline.txt'))
Get-Content (Join-Path $boot 'config.txt') | Select-String 'hdmi|spi|i2c|ignore_lcd|uart'
