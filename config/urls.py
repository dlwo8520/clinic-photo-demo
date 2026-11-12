from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from clinic.forms import StaffAuthenticationForm

urlpatterns = [
    path("login/", LoginView.as_view(authentication_form=StaffAuthenticationForm, template_name="registration/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", include("clinic.urls")),
]
