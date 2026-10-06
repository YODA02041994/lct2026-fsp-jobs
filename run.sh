#!/usr/bin/env bash
# Запуск без Docker (нужен Python 3.12):  ./run.sh dev   → http://localhost:8000
#   ./run.sh seed     — демонстрационные данные (повторный запуск ничего не дублирует)
#   ./run.sh test     — автотесты
#   ./run.sh docker   — то же в контейнерах: http://localhost:8080
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-dev}" in
  dev)
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install -q -r backend/requirements.txt
    cd backend && ../.venv/bin/python -m app.seed && ../.venv/bin/uvicorn app.main:app --reload --port 8000 ;;
  seed) cd backend && ../.venv/bin/python -m app.seed "${@:2}" ;;
  test) cd backend && ../.venv/bin/python -m pytest -q ;;
  docker) docker compose up --build ;;
  *) sed -n '2,5p' "$0" ;;
esac
