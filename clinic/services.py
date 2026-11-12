import os
import tempfile
import uuid
from pathlib import Path
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from .images import ImageValidationError, process_image
from .models import Photo


def private_path(key):
    root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Invalid private file key")
    return path


def _duplicate(client_id, visit, upload_session):
    photo = Photo.objects.filter(client_id=client_id).first()
    if photo and (photo.visit_id != visit.pk or photo.upload_session_id != (upload_session.pk if upload_session else None)):
        raise ImageValidationError("이 사진 요청 ID는 다른 업로드에 사용되었습니다. 사진을 다시 선택해 주세요.")
    return photo


def store_photo(*, visit, uploaded_file, created_by, client_id, upload_session=None, demo_key=None, body_site=""):
    if upload_session and (upload_session.visit_id != visit.pk or upload_session.expires_at <= timezone.now()):
        raise ImageValidationError("QR이 만료되었거나 대상 방문이 일치하지 않습니다.")
    client_id = uuid.UUID(str(client_id))
    existing = _duplicate(client_id, visit, upload_session)
    if existing:
        return existing, False
    if len(body_site) > 40:
        raise ImageValidationError("촬영 부위는 40자 이내로 입력해 주세요.")
    image = process_image(uploaded_file)
    identifier = uuid.uuid4().hex
    keys = {"original_key": f"originals/{identifier}.bin", "file_key": f"images/{identifier}.jpg", "thumbnail_key": f"thumbs/{identifier}.jpg"}
    temporary_paths, published_paths = [], []
    try:
        staging = private_path(".staging")
        staging.mkdir(parents=True, exist_ok=True)
        for key, data in [(keys["original_key"], image.original), (keys["file_key"], image.display), (keys["thumbnail_key"], image.thumbnail)]:
            destination = private_path(key)
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=staging, suffix=".tmp")
            temporary = Path(name)
            temporary_paths.append(temporary)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            published_paths.append(destination)
        with transaction.atomic():
            # Recheck after expensive conversion so expiration during conversion is honored.
            if upload_session and upload_session.expires_at <= timezone.now():
                raise ImageValidationError("QR이 만료되었습니다. PC에서 새 QR을 생성해 주세요.")
            photo = Photo.objects.create(visit=visit, created_by=created_by, client_id=client_id,
                                         upload_session=upload_session, demo_key=demo_key, body_site=body_site.strip(),
                                         width=image.width, height=image.height, **keys)
        return photo, True
    except Exception as exc:
        for path in published_paths:
            path.unlink(missing_ok=True)
        if isinstance(exc, IntegrityError):
            existing = _duplicate(client_id, visit, upload_session)
            if existing:
                return existing, False
        raise
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)
