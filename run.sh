#!/usr/bin/env bash
# Запуск без Docker (нужен Python 3.12):  ./run.sh dev   → http://localhost:8000 (другой порт: PORT=8015 ./run.sh dev)
#   ./run.sh seed     — демонстрационные данные (повторный запуск ничего не дублирует)
#   ./run.sh test     — автотесты
#   ./run.sh docker   — то же в контейнерах: http://localhost:8080
#   ./run.sh smoke    — проверка сквозного сценария по HTTP (BASE=http://localhost:8000 ./run.sh smoke для запуска без Docker)
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-dev}" in
  dev)
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install -q -r backend/requirements.txt
    cd backend && ../.venv/bin/python -m app.seed && FSP_PUBLIC_URL="${FSP_PUBLIC_URL:-http://localhost:${PORT:-8000}}" ../.venv/bin/uvicorn app.main:app --reload --port "${PORT:-8000}" ;;
  seed) cd backend && ../.venv/bin/python -m app.seed "${@:2}" ;;
  test)
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install -q -r backend/requirements-dev.txt
    cd backend && ../.venv/bin/python -m pytest -q ;;
  smoke) python3 scripts/smoke_http.py --base "${BASE:-http://localhost:${PORT:-8080}}" ;;
  docker) docker compose up --build ;;
  *) sed -n '2,6p' "$0" ;;
esac
