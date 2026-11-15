$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

Write-Host "Installing VideoKit in editable mode..."
python -m pip install -e .\python-package
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running fast edit-plan tests..."
python -m unittest discover -s .\Tests\videokit_edit -p "test_edit_plan.py" -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Rendering the VideoKit cuts..."
python .\Tests\videokit_edit\edit_video.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Verifying the rendered outputs..."
python -m unittest discover -s .\Tests\videokit_edit -p "test_outputs.py" -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. See Tests\videokit_edit\output."
