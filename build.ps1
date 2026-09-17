param(
    [switch]$Installer,
    [string]$Version = "1.0.1"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path "third_party\rclone.exe")) {
    throw "Missing third_party\rclone.exe. Place the Windows rclone executable there before building the installer."
}

python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean DriveDesk.spec

if ($Installer) {
    $iscc = Get-Command iscc -ErrorAction SilentlyContinue
    if (-not $iscc) { throw "Inno Setup is required for -Installer. Install it from https://jrsoftware.org/isinfo.php" }
    & $iscc.Source "/DAppVersion=$Version" "installer\DriveDesk.iss"
}
