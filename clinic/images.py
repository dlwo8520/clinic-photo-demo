import io
import warnings
from dataclasses import dataclass
from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

HEIF_SUPPORTED = False
HEIF_INFO = {}
try:
    import pillow_heif
    pillow_heif.register_heif_opener(thumbnails=False)
    HEIF_INFO = pillow_heif.libheif_info()
    # HEIF_INFO['HEIF'] describes an encoder; uploads require a decoder only.
    HEIF_SUPPORTED = bool(HEIF_INFO.get("decoders"))
except (ImportError, OSError, RuntimeError):
    pass

MAX_PIXELS = 40_000_000
MAX_SIDE = 12000
MIN_SIDE = 64
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class ImageValidationError(ValueError):
    pass


@dataclass
class ProcessedImage:
    original: bytes
    display: bytes
    thumbnail: bytes
    width: int
    height: int


def process_image(uploaded_file):
    if uploaded_file.size > settings.MAX_UPLOAD_BYTES:
        raise ImageValidationError("사진 한 장은 20MB 이하여야 합니다.")
    uploaded_file.seek(0)
    raw = uploaded_file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(raw) > settings.MAX_UPLOAD_BYTES:
        raise ImageValidationError("사진 한 장은 20MB 이하여야 합니다.")
    looks_heif = len(raw) > 12 and raw[4:8] == b"ftyp"
    if looks_heif and not HEIF_SUPPORTED:
        raise ImageValidationError("이 서버에서는 HEIC/HEIF 변환을 사용할 수 없습니다. 아이폰에서 JPEG로 변환해 올려 주세요.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in {"JPEG", "PNG", "HEIF", "HEIC"}:
                    raise ImageValidationError("JPEG, PNG, HEIC/HEIF 사진만 지원합니다.")
                w, h = source.size
                if min(w, h) < MIN_SIDE or max(w, h) > MAX_SIDE or w * h > MAX_PIXELS:
                    raise ImageValidationError("해상도는 가로·세로 64px 이상, 각 변 12,000px 이하, 총 4천만 화소 이하여야 합니다.")
                # Preserve original bytes, but bound display buffers for the 512MB demo.
                # JPEG draft decoding also avoids decoding the full camera resolution.
                source.draft("RGB", (2400, 2400))
                source.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                source.load()  # Decode fully before accepting (not just file suffix or header).
                oriented = ImageOps.exif_transpose(source)
                # A fresh RGB canvas strips EXIF/GPS, XMP, comments and other metadata.
                if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                    rgba = oriented.convert("RGBA")
                    clean = Image.new("RGB", rgba.size, "white")
                    clean.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    clean = Image.new("RGB", oriented.size)
                    clean.paste(oriented.convert("RGB"))
                display = io.BytesIO()
                clean.save(display, format="JPEG", quality=92, optimize=True)
                width, height = clean.size
                clean.thumbnail((320, 320), Image.Resampling.LANCZOS)
                thumbnail = io.BytesIO()
                clean.save(thumbnail, format="JPEG", quality=85, optimize=True)
                return ProcessedImage(raw, display.getvalue(), thumbnail.getvalue(), width, height)
    except ImageValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageValidationError("이미지 해상도가 너무 큽니다. 4천만 화소 이하로 줄여 주세요.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
        reason = "HEIC/HEIF를 읽을 수 없습니다. 손상 여부를 확인하거나 JPEG로 변환해 주세요." if looks_heif else "올바른 이미지가 아니거나 파일이 손상되었습니다. JPEG 또는 PNG 사진을 선택해 주세요."
        raise ImageValidationError(reason) from None
