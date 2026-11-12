from django.contrib.auth.views import LogoutView
from django.urls import include, path
from clinic.auth import ClinicLoginView

urlpatterns = [
    path("login/", ClinicLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", include("clinic.urls")),
]
