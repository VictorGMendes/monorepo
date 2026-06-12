Write-Output "Formating (ruff format --diff) ..."; python -m ruff format --diff
Write-Output "Lintting (ruff check -n) ..."; python -m ruff check -n
Write-Output "Type Checking (ty check) ..."; python -m ty check