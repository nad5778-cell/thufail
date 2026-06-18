# Run this from inside the thufail project folder in a VS Code PowerShell terminal.
# Sets up a Python 3.11 venv and installs all dependencies.

$python311 = "py -3.11"

Write-Host "Checking for Python 3.11..."
& py -3.11 --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.11 not found. Install it from https://www.python.org/downloads/release/python-3119/ (check 'Add python.exe to PATH'), then re-run this script."
    exit 1
}

Write-Host "Creating virtual environment (venv)..."
py -3.11 -m venv venv

Write-Host "Activating venv..."
.\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host ""
Write-Host "Done. In VS Code, press Ctrl+Shift+P -> 'Python: Select Interpreter' -> choose the one inside .\venv"
Write-Host "Then run, e.g.:"
Write-Host '  python -m thufail.checker mydata.xlsx --id-column NATIONAL_IDENTITY --output-csv flagged.csv'
