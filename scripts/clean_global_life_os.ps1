# Remove accidental GLOBAL installs of this package (use .venv for development).
# Run when NOT in a venv (deactivate first). Safe to run repeatedly.
$ErrorActionPreference = "Continue"
Write-Host "Removing editable 'life-os' from global Python interpreters (if present)..."
try {
    py -3 -m pip uninstall life-os -y 2>&1 | Out-Host
} catch {}
try {
    $py312 = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    if (Test-Path $py312) {
        & $py312 -m pip uninstall life-os -y 2>&1 | Out-Host
    }
} catch {}
Write-Host "Done. Install only via: .\scripts\install.ps1  then  .\.venv\Scripts\Activate.ps1"
