#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/render-env.sh"
# Refuse an ephemeral fallback; create directories only after disk verification.
python -m config.prepare_runtime
python manage.py migrate --noinput
python manage.py check --deploy --fail-level WARNING
if [[ "${CLINIC_SEED_DEMO:-0}" == "1" ]]; then
  python manage.py seed_demo
fi
# Verify this deployment's actual Linux codec, not only package installation.
python manage.py check_heif
# One SQLite writer process, two threads so polling can continue during upload.
# Omit access logs: request paths contain short-lived QR credentials.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 --threads 2 --timeout 180 --graceful-timeout 30 \
  --max-requests 500 --max-requests-jitter 50 --access-logfile /dev/null --error-logfile -
