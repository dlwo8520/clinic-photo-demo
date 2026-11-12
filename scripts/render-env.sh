#!/usr/bin/env bash
# The public hostname is assigned during service creation. Export Render's
# actual public URL for Django at both build and start, before importing settings.
# Explicit Dashboard values take precedence (e.g. for a custom domain).
if [[ "${RENDER:-}" == "true" ]]; then
  export QR_BASE_URL="${QR_BASE_URL:-${RENDER_EXTERNAL_URL:?Render public HTTPS URL is unavailable}}"
  export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-${RENDER_EXTERNAL_HOSTNAME:?Render public hostname is unavailable}}"
fi
