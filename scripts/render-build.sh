#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/render-env.sh"
python -m pip install -r requirements.txt
# No migrate/seed here: the persistent disk is NOT available during build.
python manage.py collectstatic --noinput
