#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/render-env.sh"
python -m pip install -r requirements.txt
# Runtime-only data: the start command migrates and seeds its own temp directory.
python manage.py collectstatic --noinput
