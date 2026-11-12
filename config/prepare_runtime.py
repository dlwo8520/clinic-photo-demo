"""Prepare the temporary data directory selected for this service start."""
import os
import tempfile
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.conf import settings
    if settings.DEBUG:
        raise SystemExit("Production startup requires DJANGO_DEBUG=0")
    data_dir = settings.DATA_DIR.resolve()
    if settings.ON_RENDER:
        if not (settings.EPHEMERAL_DEMO or settings.STORAGE_MODE == "ephemeral"):
            raise SystemExit("The Free interview deployment requires CLINIC_EPHEMERAL_DEMO=1")
        temporary_root = Path(tempfile.gettempdir()).resolve()
        if not data_dir.is_relative_to(temporary_root) or data_dir == temporary_root:
            raise SystemExit("The Free demo data directory must be inside the server temporary directory")
    data_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.PRIVATE_MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
    print("Demo data directory is ready; migrations may now run.")


if __name__ == "__main__":
    main()
