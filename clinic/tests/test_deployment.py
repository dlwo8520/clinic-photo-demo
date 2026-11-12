"""Production configuration is validated before touching a mounted data disk."""

from io import StringIO
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, DatabaseError
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from config import prepare_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_ENV_NAMES = (
    "DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "QR_BASE_URL",
    "CLINIC_DATA_DIR", "RENDER", "RENDER_EXTERNAL_HOSTNAME", "CLINIC_DEMO_PASSWORD",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)
IMPORT_SETTINGS_SCRIPT = """
import json
import config.settings as s
print(json.dumps({
    'debug': s.DEBUG,
    'hosts': s.ALLOWED_HOSTS,
    'qr': s.QR_BASE_URL,
    'database': str(s.DATABASES['default']['NAME']),
    'media': str(s.PRIVATE_MEDIA_ROOT),
    'static_root': str(s.STATIC_ROOT),
    'session_secure': s.SESSION_COOKIE_SECURE,
    'csrf_secure': s.CSRF_COOKIE_SECURE,
    'redirect': s.SECURE_SSL_REDIRECT,
    'proxy_header': s.SECURE_PROXY_SSL_HEADER,
    'hsts': s.SECURE_HSTS_SECONDS,
    'middleware': s.MIDDLEWARE,
    'redirect_exempt': s.SECURE_REDIRECT_EXEMPT,
}))
"""


class ProductionSettingsTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        # Deliberately absent: importing settings during a build must not create it.
        self.data_dir = (Path(self.temporary.name) / "mounted-data").resolve()
        self.synthetic_secret = "test-only-7zQ9pK2mV6sR3tY8uB5dN1fL4gH0wE9aC6xJ2oP7rS5vD"

    def run_settings(self, changes=None, removed=()):
        env = os.environ.copy()
        for name in SETTINGS_ENV_NAMES:
            env.pop(name, None)
        env.update({
            "PYTHONUTF8": "1",
            "DJANGO_DEBUG": "0",
            "DJANGO_SECRET_KEY": self.synthetic_secret,
            "DJANGO_ALLOWED_HOSTS": "clinic.example.com",
            "QR_BASE_URL": "https://clinic.example.com",
            "CLINIC_DATA_DIR": str(self.data_dir),
        })
        env.update(changes or {})
        for name in removed:
            env.pop(name, None)
        result = subprocess.run(
            [sys.executable, "-c", IMPORT_SETTINGS_SCRIPT],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        # Assertions can report errors without ever including even the test key.
        result.stdout = result.stdout.replace(self.synthetic_secret, "[redacted]")
        result.stderr = result.stderr.replace(self.synthetic_secret, "[redacted]")
        return result

    def assert_settings_rejected(self, changes=None, removed=()):
        result = self.run_settings(changes, removed)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertFalse(self.data_dir.exists(), "Invalid configuration must not create storage directories")

    def test_valid_production_settings_use_disk_and_secure_defaults_without_creating_disk(self):
        result = self.run_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads(result.stdout)
        self.assertFalse(settings["debug"])
        self.assertEqual(settings["hosts"], ["clinic.example.com"])
        self.assertEqual(settings["qr"], "https://clinic.example.com")
        self.assertEqual(Path(settings["database"]), self.data_dir / "db.sqlite3")
        self.assertEqual(Path(settings["media"]), self.data_dir / "private_media")
        self.assertTrue(settings["static_root"])
        self.assertTrue(settings["session_secure"])
        self.assertTrue(settings["csrf_secure"])
        self.assertTrue(settings["redirect"])
        self.assertEqual(settings["proxy_header"], ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertGreaterEqual(settings["hsts"], 3600)
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings["middleware"])
        self.assertTrue(any("healthz" in pattern for pattern in settings["redirect_exempt"]))
        self.assertFalse(self.data_dir.exists(), "Build-time settings import must not require a writable data mount")

    def test_production_requires_explicit_strong_secret(self):
        self.assert_settings_rejected(removed=["DJANGO_SECRET_KEY"])
        for secret in ["short", "x" * 64, "django-insecure-" + "test" * 20]:
            with self.subTest(secret_kind="insecure"):
                self.assert_settings_rejected({"DJANGO_SECRET_KEY": secret})

    def test_production_requires_absolute_data_directory(self):
        self.assert_settings_rejected(removed=["CLINIC_DATA_DIR"])
        self.assert_settings_rejected({"CLINIC_DATA_DIR": "relative-data"})

    def test_production_requires_explicit_https_qr_origin(self):
        self.assert_settings_rejected(removed=["QR_BASE_URL"])
        self.assert_settings_rejected({"QR_BASE_URL": "http://clinic.example.com"})

    def test_production_rejects_local_and_non_public_qr_hosts(self):
        for host in ["localhost", "demo.localhost", "127.0.0.1", "192.168.1.42", "10.0.0.8", "172.16.0.8", "169.254.1.2", "[::1]", "[fd00::1]"]:
            with self.subTest(host=host):
                self.assert_settings_rejected({"QR_BASE_URL": f"https://{host}", "DJANGO_ALLOWED_HOSTS": host})

    def test_production_rejects_wildcard_missing_or_mismatched_hosts(self):
        self.assert_settings_rejected(removed=["DJANGO_ALLOWED_HOSTS"])
        self.assert_settings_rejected({"DJANGO_ALLOWED_HOSTS": "*"})
        self.assert_settings_rejected({"DJANGO_ALLOWED_HOSTS": "another.example.com"})

    def test_render_hostname_can_supply_allowed_hosts(self):
        result = self.run_settings(
            {"RENDER_EXTERNAL_HOSTNAME": "clinic-demo.onrender.com", "QR_BASE_URL": "https://clinic-demo.onrender.com"},
            removed=["DJANGO_ALLOWED_HOSTS"],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hosts"], ["clinic-demo.onrender.com"])
        self.assertFalse(self.data_dir.exists())

    def test_render_cannot_enable_debug(self):
        self.assert_settings_rejected({"RENDER": "true", "DJANGO_DEBUG": "1"})


class DeploymentHealthTests(TestCase):
    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^healthz/$"])
    def test_health_check_is_public_and_exempt_from_https_redirect(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertTrue(any(query["sql"].strip().upper() == "SELECT 1" for query in queries))

    def test_health_check_returns_503_when_database_is_unavailable(self):
        with patch("clinic.views.connection.cursor", side_effect=DatabaseError("database unavailable")):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})


class RuntimeStorageTests(SimpleTestCase):
    def test_render_refuses_missing_mount_and_outside_mount_without_creating_storage(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = (Path(temporary) / "persistent-data").resolve()
            media_dir = data_dir / "private_media"
            with override_settings(DEBUG=False, ON_RENDER=True, DATA_DIR=data_dir, PRIVATE_MEDIA_ROOT=media_dir):
                for mounted in [False, True]:
                    with self.subTest(mounted=mounted):
                        with patch("config.prepare_runtime.os.path.ismount", return_value=mounted):
                            with self.assertRaises(SystemExit) as error:
                                prepare_runtime.main()
                        expected = "not mounted" if not mounted else "subdirectory"
                        self.assertIn(expected, str(error.exception))
                        self.assertFalse(data_dir.exists())
                        self.assertFalse(media_dir.exists())

    def test_generic_production_startup_creates_storage_and_can_repeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = (Path(temporary) / "persistent-data").resolve()
            media_dir = data_dir / "private_media"
            with override_settings(DEBUG=False, ON_RENDER=False, DATA_DIR=data_dir, PRIVATE_MEDIA_ROOT=media_dir):
                with redirect_stdout(StringIO()):
                    prepare_runtime.main()
                    prepare_runtime.main()
            self.assertTrue(data_dir.is_dir())
            self.assertTrue(media_dir.is_dir())
            self.assertFalse((data_dir / "db.sqlite3").exists(), "Preparing storage must not create or migrate the database")


class ProductionSeedTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.settings_override = override_settings(DEBUG=False, PRIVATE_MEDIA_ROOT=Path(self.temporary.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def test_production_seed_requires_password_before_creating_account(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLINIC_DEMO_PASSWORD", None)
            with self.assertRaises(CommandError):
                call_command("seed_demo", stdout=StringIO())
        self.assertFalse(get_user_model().objects.filter(username="dlwo8520").exists())

    def test_production_seed_uses_env_password_without_printing_or_resetting_it(self):
        password = "Production-demo-pass!2026"
        output = StringIO()
        with patch.dict(os.environ, {"CLINIC_DEMO_PASSWORD": password}):
            call_command("seed_demo", stdout=output)
        account = get_user_model().objects.get(username="dlwo8520")
        self.assertTrue(account.check_password(password))
        self.assertNotIn(password, output.getvalue())
        self.assertNotIn("초기 비밀번호:", output.getvalue())
        # Re-running after a first seed must not need or change a password.
        second_output = StringIO()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLINIC_DEMO_PASSWORD", None)
            call_command("seed_demo", stdout=second_output)
        account.refresh_from_db()
        self.assertTrue(account.check_password(password))
        self.assertNotIn(password, second_output.getvalue())
