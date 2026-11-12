"""Validate Render's mounted disk before any database or upload directory write."""
import os
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.conf import settings
    if settings.DEBUG:
        raise SystemExit("Production startup requires DJANGO_DEBUG=0")
    data_dir = settings.DATA_DIR.resolve()
    if settings.ON_RENDER:
        mount = Path("/var/data")
        if not os.path.ismount(mount):
            raise SystemExit("Persistent disk /var/data is not mounted. Refusing to create an ephemeral database.")
        if not data_dir.is_relative_to(mount) or data_dir == mount:
            raise SystemExit("CLINIC_DATA_DIR must be a subdirectory of persistent mount /var/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.PRIVATE_MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
    print("Persistent data directory is ready; migrations may now run.")


if __name__ == "__main__":
    main()
