from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import StaffAuthenticationForm


class ClinicLoginView(LoginView):
    authentication_form = StaffAuthenticationForm
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(demo_login=settings.DEMO_LOGIN_ENABLED, **kwargs)

    def post(self, request, *args, **kwargs):
        if not settings.DEMO_LOGIN_ENABLED:
            return super().post(request, *args, **kwargs)
        if request.POST.get("demo") != "staff":
            return HttpResponseForbidden("데모 접속 버튼을 선택해 주세요.")
        user = get_user_model().objects.filter(username="dlwo8520", is_active=True, is_staff=True).first()
        if user is None:
            return HttpResponseForbidden("데모 계정이 준비되지 않았습니다.")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        target = request.POST.get("next", "")
        if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
            return redirect(target)
        return redirect("patients")
