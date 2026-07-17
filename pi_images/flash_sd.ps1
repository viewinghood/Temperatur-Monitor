# Flash Raspberry Pi OS image to SD card (PhysicalDrive1)
# Run as Administrator
$ErrorActionPreference = 'Stop'
$ImagePath = 'C:\Users\ritchie\temp_monitor\pi_images\2023-05-03-raspios-bullseye-armhf.img'
$DiskNumber = 1

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

$disk = Get-Disk -Number $DiskNumber
Write-Host "Target: Disk $DiskNumber - $($disk.FriendlyName) - $([math]::Round($disk.Size/1GB,1)) GB"
Write-Host "Image:  $ImagePath ($([math]::Round((Get-Item $ImagePath).Length/1GB,2)) GB)"

# Dismount all volumes on SD
Get-Partition -DiskNumber $DiskNumber | ForEach-Object {
    if ($_.DriveLetter) {
        Write-Host "Removing drive letter $($_.DriveLetter):"
        Remove-PartitionAccessPath -DiskNumber $DiskNumber -PartitionNumber $_.PartitionNumber -AccessPath "$($_.DriveLetter):\" -ErrorAction SilentlyContinue
    }
}
Set-Disk -Number $DiskNumber -IsReadOnly $false -ErrorAction SilentlyContinue
Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction SilentlyContinue

Write-Host 'Writing image (5-15 min)...'
$img = [System.IO.File]::OpenRead($ImagePath)
try {
    $path = "\\.\PhysicalDrive$DiskNumber"
    $dest = New-Object System.IO.FileStream(
        $path,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::ReadWrite
    )
    try {
        $buf = New-Object byte[] (4MB)
        $total = $img.Length
        $done = 0L
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        while (($read = $img.Read($buf, 0, $buf.Length)) -gt 0) {
            $dest.Write($buf, 0, $read)
            $done += $read
            if ($sw.Elapsed.TotalSeconds -ge 10) {
                $pct = [math]::Round(100 * $done / $total, 1)
                Write-Host ("  {0}% ({1} MB)" -f $pct, [math]::Round($done/1MB))
                $sw.Restart()
            }
        }
        $dest.Flush()
    } finally { $dest.Close() }
} finally { $img.Close() }

Write-Host 'Rescanning disk...'
Update-Disk -Number $DiskNumber
Start-Sleep -Seconds 4
Get-Partition -DiskNumber $DiskNumber | Format-Table PartitionNumber, DriveLetter, Size, Type
Write-Host 'Flash complete.'
