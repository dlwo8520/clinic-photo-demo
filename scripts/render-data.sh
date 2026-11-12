#!/usr/bin/env bash
# Each service start is a new demo. Never delete or overwrite the current data.
# Keep this exported path for all management commands and Gunicorn workers.
if [[ "${CLINIC_EPHEMERAL_DEMO:-0}" == "1" || "${CLINIC_STORAGE_MODE:-}" == "ephemeral" ]]; then
  export CLINIC_DATA_DIR="$(mktemp -d "${TMPDIR:-/tmp}/goodmona-demo.XXXXXX")"
fi
