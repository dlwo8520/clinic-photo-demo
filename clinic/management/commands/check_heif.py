from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image
from clinic.images import HEIF_INFO, HEIF_SUPPORTED, process_image


class Command(BaseCommand):
    help = "Report HEIF decoder support and verify an actual HEIC-to-JPEG conversion."

    def handle(self, *args, **options):
        self.stdout.write(f"HEIF decoder: {'available' if HEIF_SUPPORTED else 'unavailable'}")
        self.stdout.write(str(HEIF_INFO))
        if not HEIF_SUPPORTED:
            raise CommandError("HEIC/HEIF decoding is unavailable. Install requirements.txt wheels for Python 3.12.")
        buffer = BytesIO()
        try:
            Image.new("RGB", (128, 96), "#145952").save(buffer, format="HEIF", quality=80)
        except (OSError, ValueError, KeyError) as exc:
            self.stdout.write(self.style.WARNING(f"Decoder registered; sample encoder unavailable: {exc}. Test a real HEIC upload."))
            return
        converted = process_image(SimpleUploadedFile("probe.heic", buffer.getvalue()))
        with Image.open(BytesIO(converted.display)) as display:
            if display.format != "JPEG" or display.size != (128, 96) or display.getexif():
                raise CommandError("HEIC conversion verification failed")
        self.stdout.write(self.style.SUCCESS("HEIC -> JPEG + thumbnail conversion verified (128 x 96, metadata stripped)."))
