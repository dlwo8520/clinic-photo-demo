"""Native login forms must keep a usable same-origin referrer policy."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class LoginCsrfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_user(
            username="csrf-staff", password="csrf-test-password", is_staff=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def form_data(self, secure=False):
        response = self.client.get("/login/", secure=secure)
        # no-referrer would turn ordinary non-CORS POST Origin into null in
        # browsers, even when this form submits to its own origin.
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        return {
            "username": "csrf-staff",
            "password": "csrf-test-password",
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        }

    def test_native_same_origin_login_accepts_cookie_and_form_token(self):
        response = self.client.post(
            "/login/", self.form_data(), HTTP_ORIGIN="http://testserver"
        )
        self.assertRedirects(response, "/patients/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

    def test_https_form_can_use_same_origin_referer_without_origin(self):
        response = self.client.post(
            "/login/", self.form_data(secure=True), secure=True,
            HTTP_REFERER="https://testserver/login/",
        )
        self.assertRedirects(response, "/patients/", fetch_redirect_response=False)

    def test_null_and_foreign_origins_are_still_rejected(self):
        for origin in ("null", "https://untrusted.example"):
            with self.subTest(origin=origin):
                response = self.client.post(
                    "/login/", self.form_data(), HTTP_ORIGIN=origin
                )
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("_auth_user_id", self.client.session)
