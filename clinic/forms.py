from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Visit


class StaffAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError("데모 직원 계정으로 로그인해 주세요.", code="not_staff")


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["week", "visited_on"]
