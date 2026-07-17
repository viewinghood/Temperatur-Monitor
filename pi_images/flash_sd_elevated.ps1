$ErrorActionPreference = 'Stop'
$Log = 'C:\Users\ritchie\temp_monitor\pi_images\flash_sd.log'
Start-Transcript -Path $Log -Force
try {
    & 'C:\Users\ritchie\temp_monitor\pi_images\flash_sd.ps1'
} finally {
    Stop-Transcript
}
