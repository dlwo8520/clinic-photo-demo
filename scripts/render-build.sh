#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/render-env.sh"
python -m pip install -r requirements.txt
# Initialization happens on start, in the actual ephemeral runtime filesystem.
python manage.py collectstatic --noinput
