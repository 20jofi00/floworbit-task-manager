#!/usr/bin/env bash
set -euo pipefail

uv sync --locked

uv run python manage.py collectstatic --noinput --settings=config.settings.prod
uv run python manage.py migrate --noinput --settings=config.settings.prod
