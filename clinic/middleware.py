from django.conf import settings
from django.http import JsonResponse


class PrivateResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "private, no-store, max-age=0"
            response["Referrer-Policy"] = settings.SECURE_REFERRER_POLICY
        return response


class UploadSizeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/uploads/") and request.method == "POST":
            try:
                length = int(request.META.get("CONTENT_LENGTH") or "0")
            except ValueError:
                return JsonResponse({"error": "올바르지 않은 요청 크기입니다."}, status=400)
            if length > settings.MAX_BATCH_BYTES:
                return JsonResponse({"error": "한 번에 100MB 이하로 전송해 주세요. 사진을 나누어 올릴 수 있습니다."}, status=413)
        return self.get_response(request)
