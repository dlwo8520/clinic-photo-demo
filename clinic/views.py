import io
import json
import logging
import uuid
from functools import wraps
import qrcode
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Max, Q
from django.db import connection, DatabaseError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from .forms import VisitForm
from .images import HEIF_SUPPORTED, ImageValidationError
from .models import Patient, Visit, Photo, UploadSession
from .services import private_path, store_photo

logger = logging.getLogger(__name__)


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def staff_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        api = request.path.startswith("/api/")
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다. 새로고침 후 다시 로그인해 주세요."}, status=401) if api else redirect_to_login(request.get_full_path())
        if not request.user.is_active or not request.user.is_staff:
            return JsonResponse({"error": "직원 계정으로 로그인해 주세요."}, status=403)
        return view(request, *args, **kwargs)
    return wrapped


def serialize_photo(photo):
    return {"id": photo.pk, "url": reverse("photo", args=[photo.pk]), "thumbnail_url": reverse("thumbnail", args=[photo.pk]),
            "body_site": photo.body_site, "created_at": photo.created_at.isoformat()}


def serialize_visit(visit):
    return {"id": visit.pk, "week": visit.week, "visited_on": visit.visited_on.isoformat(), "label": visit.label,
            "photo_count": getattr(visit, "photo_count", None) if hasattr(visit, "photo_count") else visit.photos.count()}


def photo_payload(visit):
    photos = [serialize_photo(p) for p in visit.photos.all()]
    return {"visit_id": visit.pk, "photos": photos, "photo_count": len(photos)}


def resolve_session(token):
    if not 30 <= len(token) <= 100:
        return None
    return UploadSession.objects.select_related("visit__patient").filter(token_hash=UploadSession.hash_token(token)).first()


@require_GET
def home(request):
    return redirect("patients")


@staff_required
@require_GET
def patients(request):
    q = request.GET.get("q", "").strip()[:100]
    items = Patient.objects.annotate(visit_count=Count("visits"), last_visit=Max("visits__visited_on"))
    if q:
        items = items.filter(Q(name__icontains=q) | Q(chart_number__icontains=q))
    return render(request, "clinic/patients.html", {"patients": items, "q": q})


@staff_required
@require_GET
@ensure_csrf_cookie
def compare(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    visits = list(patient.visits.annotate(photo_count=Count("photos")))
    right = visits[-1] if visits else None
    left = visits[-2] if len(visits) > 1 else (visits[0] if visits else None)
    initial = {"visits": [serialize_visit(v) for v in visits], "left": photo_payload(left) if left else {"visit_id": None, "photos": []},
               "right": photo_payload(right) if right else {"visit_id": None, "photos": []}}
    return render(request, "clinic/compare.html", {"patient": patient, "visits": visits, "left_visit": left, "right_visit": right, "initial_data": initial})


@staff_required
@require_POST
def create_visit(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "주차와 방문일을 올바르게 입력해 주세요."}, status=400)
    form = VisitForm(data)
    if not form.is_valid():
        return JsonResponse({"error": "주차(1~520)와 올바른 방문일을 입력해 주세요.", "fields": form.errors.get_json_data()}, status=400)
    visit = form.save(commit=False)
    visit.patient = patient
    visit.save()
    return JsonResponse({"visit": serialize_visit(visit)}, status=201)


@staff_required
@require_GET
def visit_photos(request, visit_id):
    return JsonResponse(photo_payload(get_object_or_404(Visit, pk=visit_id)))


@staff_required
@require_POST
def issue_upload_session(request, visit_id):
    visit = get_object_or_404(Visit.objects.select_related("patient"), pk=visit_id)
    session, token = UploadSession.issue(visit, request.user)
    return JsonResponse({"url": settings.QR_BASE_URL + reverse("upload", args=[token]), "qr_url": reverse("qr", args=[token]),
                         "expires_at": session.expires_at.isoformat(), "patient_name": visit.patient.name,
                         "chart_number": visit.patient.chart_number, "visit_label": visit.label}, status=201)


@staff_required
@require_GET
@ensure_csrf_cookie
def upload_page(request, token):
    session = resolve_session(token)
    if not session or session.is_expired:
        return render(request, "clinic/upload_invalid.html", {"reason": "QR 만료" if session else "유효하지 않은 QR", "detail": "PC에서 새 QR을 생성한 뒤 다시 열어 주세요."}, status=410)
    return render(request, "clinic/upload.html", {"patient": session.visit.patient, "visit": session.visit, "token": token,
                                                "expires_at": session.expires_at, "heif_supported": HEIF_SUPPORTED})


@staff_required
@require_GET
def qr_image(request, token):
    session = resolve_session(token)
    if not session or session.is_expired:
        return JsonResponse({"error": "QR 만료. 새 QR을 생성해 주세요."}, status=410)
    qr = qrcode.make(settings.QR_BASE_URL + reverse("upload", args=[token]))
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@staff_required
@require_POST
def upload_photos(request, token):
    session = resolve_session(token)
    if not session or session.is_expired:
        return JsonResponse({"error": "QR 만료. PC에서 새 QR을 생성해 주세요."}, status=410)
    # The route's token is the sole authority; request IDs can never redirect storage.
    for field, expected in [("visit_id", session.visit_id), ("patient_id", session.visit.patient_id)]:
        if field in request.POST and request.POST[field] != str(expected):
            return JsonResponse({"error": "QR에 연결된 환자·방문과 요청 대상이 일치하지 않습니다."}, status=400)
    files = request.FILES.getlist("photos")
    client_ids = request.POST.getlist("client_ids")
    sites = request.POST.getlist("body_sites")
    if not files or len(files) > 20 or len(client_ids) != len(files) or (sites and len(sites) != len(files)):
        return JsonResponse({"error": "사진 1~20장과 각 사진의 요청 ID를 함께 보내 주세요."}, status=400)
    if sum(file.size for file in files) > settings.MAX_BATCH_BYTES:
        return JsonResponse({"error": "한 번에 100MB 이하로 전송해 주세요."}, status=413)
    results = []
    for index, (uploaded, raw_id) in enumerate(zip(files, client_ids)):
        result = {"client_id": raw_id}
        try:
            client_id = uuid.UUID(raw_id)
            photo, created = store_photo(visit=session.visit, uploaded_file=uploaded, created_by=request.user,
                                         client_id=client_id, upload_session=session, body_site=sites[index] if sites else "")
            result.update(status="saved" if created else "duplicate", photo=serialize_photo(photo))
        except ImageValidationError as exc:
            result.update(status="error", error=str(exc))
        except ValueError:
            result.update(status="error", error="사진 요청 ID 형식이 올바르지 않습니다. 사진을 다시 선택해 주세요.")
        except Exception:
            logger.exception("Photo storage failed for upload session %s", session.pk)
            result.update(status="error", error="서버 저장에 실패했습니다. 이 사진만 다시 시도해 주세요.")
        results.append(result)
    return JsonResponse({"results": results})


@staff_required
@require_GET
def photo_file(request, photo_id, thumbnail=False):
    photo = get_object_or_404(Photo, pk=photo_id)
    try:
        path = private_path(photo.thumbnail_key if thumbnail else photo.file_key)
        stream = path.open("rb")
    except (OSError, ValueError):
        raise Http404("사진 파일을 찾을 수 없습니다.") from None
    return FileResponse(stream, content_type="image/jpeg", filename=f"photo-{photo.pk}.jpg")
