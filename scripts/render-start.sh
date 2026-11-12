#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/render-env.sh"
source "$(dirname "${BASH_SOURCE[0]}")/render-data.sh"
# A new service start gets a fresh directory; Gunicorn worker recycling keeps it.
python -m config.prepare_runtime
python manage.py migrate --noinput
python manage.py check --deploy --fail-level WARNING
python manage.py seed_demo
# Verify this deployment's actual Linux codec, not only package installation.
python manage.py check_heif
# One SQLite process, two threads so polling can continue during upload.
# Omit access logs: request paths contain short-lived QR credentials.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 --threads 2 --timeout 180 --graceful-timeout 30 \
  --max-requests 500 --max-requests-jitter 50 --access-logfile /dev/null --error-logfile -
