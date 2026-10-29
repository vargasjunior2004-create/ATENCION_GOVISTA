param(
    [ValidateSet('check', 'test', 'test-core', 'lint')]
    [string]$Task = 'test'
)

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { 'python' }

switch ($Task) {
    'check' { & $PythonBin manage.py check }
    'test' { & $PythonBin manage.py test }
    'test-core' { & $PythonBin manage.py test core }
    'lint' {
        if (Get-Command ruff -ErrorAction SilentlyContinue) {
            ruff check .
        } else {
            Write-Output 'lint: ruff no está instalado todavía; se activará en la Fase 8.'
        }
    }
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
