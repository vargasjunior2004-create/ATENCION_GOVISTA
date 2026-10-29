#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PYTHON_BIN:-}" ]]; then
  :
elif [[ -x .venv/bin/python ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

case "${1:-test}" in
  check)
    "$PYTHON_BIN" manage.py check
    ;;
  test)
    "$PYTHON_BIN" manage.py test
    ;;
  test-core)
    "$PYTHON_BIN" manage.py test core
    ;;
  lint)
    if command -v ruff >/dev/null 2>&1; then
      ruff check .
    else
      echo "lint: ruff no está instalado todavía; se activará en la Fase 8."
    fi
    ;;
  *)
    echo "Uso: $0 {check|test|test-core|lint}" >&2
    exit 2
    ;;
esac
