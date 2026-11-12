"""DB-backed acceptance and access-control tests for the photo prototype."""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import json
import tempfile
import uuid
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from clinic.images import HEIF_SUPPORTED
from clinic.models import Patient, Photo, UploadSession, Visit


def image_file(name="image.jpg", *, size=(96, 80), fmt="JPEG", exif=None):
    output = BytesIO()
    image = Image.new("RGB", size, "#356e68")
    options = {"exif": exif} if exif else {}
    image.save(output, format=fmt, **options)
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/jpeg")


def response_bytes(response):
    try:
        return b"".join(response.streaming_content) if response.streaming else response.content
    finally:
        response.close()


class PhotoWorkflowTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            PRIVATE_MEDIA_ROOT=Path(self.media.name),
            QR_BASE_URL="http://192.168.1.42:8000",
            ALLOWED_HOSTS=["testserver", "192.168.1.42"],
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media.cleanup)
        self.staff = get_user_model().objects.create_user(
            username="staff", password="a-test-password", is_staff=True
        )
        self.client.force_login(self.staff)
        self.patient = Patient.objects.create(name="김하나", chart_number="TEST-1001")
        self.namesake = Patient.objects.create(name="김하나", chart_number="TEST-1002")
        self.first = Visit.objects.create(
            patient=self.patient, week=1, visited_on=date(2026, 10, 5)
        )
        self.second = Visit.objects.create(
            patient=self.patient, week=2, visited_on=date(2026, 10, 12)
        )
        self.empty = Visit.objects.create(
            patient=self.patient, week=3, visited_on=date(2026, 10, 19)
        )
        self.other_visit = Visit.objects.create(
            patient=self.namesake, week=1, visited_on=date(2026, 10, 5)
        )

    def make_session(self, visit=None):
        visit = visit or self.empty
        response = self.client.post(f"/api/visits/{visit.pk}/upload-sessions/")
        self.assertIn(response.status_code, [200, 201], response.content)
        payload = response.json()
        token = urlparse(payload["url"]).path.strip("/").split("/")[-1]
        return token, payload

    def upload(self, token, files=None, client_ids=None, **extra):
        files = [image_file()] if files is None else files
        ids = client_ids or [str(uuid.uuid4()) for _ in files]
        data = {"photos": files, "client_ids": ids, "body_sites": ["정수리"] * len(files)}
        data.update(extra)
        return self.client.post(f"/api/uploads/{token}/photos/", data)

    def test_name_search_shows_namesakes_chart_numbers_and_counts(self):
        response = self.client.get("/patients/", {"q": "하나"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TEST-1001")
        self.assertContains(response, "TEST-1002")
        patients = {p.chart_number: p for p in response.context["patients"]}
        self.assertEqual(patients["TEST-1001"].visit_count, 3)
        self.assertEqual(patients["TEST-1001"].last_visit, date(2026, 10, 19))

    def test_chart_search_filters_namesakes(self):
        response = self.client.get("/patients/", {"q": "TEST-1002"})
        self.assertContains(response, "TEST-1002")
        self.assertNotContains(response, "TEST-1001")

    def test_compare_defaults_to_previous_and_latest_including_empty(self):
        response = self.client.get(f"/patients/{self.patient.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["left_visit"].pk, self.second.pk)
        self.assertEqual(response.context["right_visit"].pk, self.empty.pk)
        self.assertEqual(response.context["initial_data"]["right"]["visit_id"], self.empty.pk)
        self.assertIn("3주차", response.context["initial_data"]["visits"][-1]["label"])

    def test_single_visit_and_no_visit_render(self):
        single = self.client.get(f"/patients/{self.namesake.pk}/")
        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.context["right_visit"].pk, self.other_visit.pk)
        no_visits = Patient.objects.create(name="무방문", chart_number="TEST-1003")
        self.assertEqual(self.client.get(f"/patients/{no_visits.pk}/").status_code, 200)

    def test_create_empty_visit_with_explicit_week_and_duplicate_week_allowed(self):
        response = self.client.post(
            f"/api/patients/{self.patient.pk}/visits/",
            json.dumps({"week": 2, "visited_on": "2026-10-14"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 201], response.content)
        visit = Visit.objects.get(pk=response.json()["visit"]["id"])
        self.assertEqual(visit.week, 2)
        self.assertEqual(visit.visited_on, date(2026, 10, 14))
        self.assertEqual(visit.photos.count(), 0)

    def test_invalid_visit_input_returns_validation_error(self):
        before = Visit.objects.count()
        for body in [{"week": 0, "visited_on": "2026-10-14"}, {"week": 2, "visited_on": "bad-date"}]:
            response = self.client.post(
                f"/api/patients/{self.patient.pk}/visits/",
                json.dumps(body), content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Visit.objects.count(), before)

    def test_qr_uses_configured_host_and_only_opaque_token(self):
        token, payload = self.make_session()
        self.assertTrue(payload["url"].startswith("http://192.168.1.42:8000/upload/"))
        self.assertGreaterEqual(len(token), 32)
        self.assertNotIn(self.patient.name, payload["url"])
        self.assertNotIn(self.patient.chart_number, payload["url"])
        session = UploadSession.objects.get(visit=self.empty)
        self.assertNotEqual(session.token_hash, token)
        self.assertGreater(session.expires_at, timezone.now())
        self.assertLessEqual(session.expires_at, timezone.now() + timedelta(minutes=11))
        qr_response = self.client.get(payload["qr_url"])
        self.assertEqual(qr_response.status_code, 200)
        self.assertIn(qr_response["Content-Type"].split(";")[0], ["image/png", "image/svg+xml"])

    def test_mobile_login_preserves_upload_return_url(self):
        token, _ = self.make_session()
        self.client.logout()
        target = f"/upload/{token}/"
        response = self.client.get(target)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_qs(urlparse(response.url).query)["next"], [target])
        self.client.force_login(self.staff)
        response = self.client.get(target)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.name)
        self.assertContains(response, self.patient.chart_number)

    def test_three_then_one_upload_preserves_db_photos_and_listing(self):
        token, _ = self.make_session()
        first_batch = self.upload(token, [image_file(f"{i}.jpg") for i in range(3)])
        self.assertEqual(first_batch.status_code, 200, first_batch.content)
        self.assertEqual([r["status"] for r in first_batch.json()["results"]], ["saved"] * 3)
        initial_ids = set(Photo.objects.filter(visit=self.empty).values_list("id", flat=True))
        self.assertEqual(len(initial_ids), 3)
        second_batch = self.upload(token)
        self.assertEqual(second_batch.json()["results"][0]["status"], "saved")
        self.assertEqual(Photo.objects.filter(visit=self.empty).count(), 4)
        photos = self.client.get(f"/api/visits/{self.empty.pk}/photos/").json()
        self.assertEqual(photos["photo_count"], 4)
        self.assertEqual(photos["visit_id"], self.empty.pk)
        self.assertTrue(initial_ids.issubset({p["id"] for p in photos["photos"]}))
        self.assertTrue(all(p["body_site"] == "정수리" for p in photos["photos"]))
        for photo in photos["photos"]:
            for url in [photo["url"], photo["thumbnail_url"]]:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response_bytes(response))
        self.assertEqual(Photo.objects.filter(visit=self.first).count(), 0)

    def test_same_request_replay_is_idempotent_for_db_and_files(self):
        token, _ = self.make_session()
        key = str(uuid.uuid4())
        first = self.upload(token, client_ids=[key]).json()["results"][0]
        files_before = sorted(str(path.relative_to(self.media.name)) for path in Path(self.media.name).rglob("*") if path.is_file())
        replay = self.upload(token, client_ids=[key]).json()["results"][0]
        self.assertEqual(first["status"], "saved")
        self.assertEqual(replay["status"], "duplicate")
        self.assertEqual(Photo.objects.count(), 1)
        self.assertEqual(first["photo"]["id"], replay["photo"]["id"])
        files_after = sorted(str(path.relative_to(self.media.name)) for path in Path(self.media.name).rglob("*") if path.is_file())
        self.assertEqual(files_before, files_after)

    def test_partial_batch_failure_and_retry_only_failed_item(self):
        token, _ = self.make_session()
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        invalid = SimpleUploadedFile("bad.jpg", b"not an image", content_type="image/jpeg")
        response = self.upload(token, [image_file(), invalid], ids)
        self.assertEqual(response.status_code, 200, response.content)
        results = response.json()["results"]
        self.assertEqual([r["status"] for r in results], ["saved", "error"])
        self.assertTrue(results[1]["error"])
        self.assertEqual(Photo.objects.count(), 1)
        retry = self.upload(token, [image_file()], [ids[1]])
        self.assertEqual(retry.json()["results"][0]["status"], "saved")
        self.assertEqual(Photo.objects.count(), 2)

    def test_other_visit_and_patient_body_cannot_override_token(self):
        token, _ = self.make_session()
        for extra in [{"visit_id": self.other_visit.pk}, {"patient_id": self.namesake.pk}]:
            response = self.upload(token, **extra)
            self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Photo.objects.count(), 0)

    def test_pc_switch_does_not_change_token_destination(self):
        token, _ = self.make_session(self.empty)
        self.client.get(f"/api/visits/{self.first.pk}/photos/")
        self.client.get(f"/api/visits/{self.other_visit.pk}/photos/")
        response = self.upload(token)
        self.assertEqual(response.json()["results"][0]["status"], "saved")
        self.assertEqual(Photo.objects.get().visit_id, self.empty.pk)
        self.assertEqual(Photo.objects.get().created_by_id, self.staff.pk)

    def test_expired_token_rejected_for_page_qr_and_upload(self):
        token, payload = self.make_session()
        UploadSession.objects.filter(visit=self.empty).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get(f"/upload/{token}/").status_code, 410)
        self.assertEqual(self.client.get(payload["qr_url"]).status_code, 410)
        self.assertEqual(self.upload(token).status_code, 410)
        self.assertEqual(Photo.objects.count(), 0)

    def test_unknown_token_rejected(self):
        token = "x" * 43
        self.assertIn(self.client.get(f"/upload/{token}/").status_code, [404, 410])
        self.assertIn(self.upload(token).status_code, [404, 410])
        self.assertEqual(Photo.objects.count(), 0)

    def test_api_and_private_photo_require_staff_login(self):
        token, _ = self.make_session()
        self.upload(token)
        photo = self.client.get(f"/api/visits/{self.empty.pk}/photos/").json()["photos"][0]
        self.client.logout()
        for url in [photo["url"], photo["thumbnail_url"]]:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302, 401, 403])
            self.assertNotEqual(response.status_code, 200)
        self.assertEqual(self.upload(token).status_code, 401)
        self.assertEqual(self.client.get(f"/api/visits/{self.empty.pk}/photos/").status_code, 401)
        ordinary = get_user_model().objects.create_user("ordinary", password="test")
        self.client.force_login(ordinary)
        self.assertEqual(self.client.get(f"/patients/{self.patient.pk}/").status_code, 403)
        self.assertEqual(self.client.get(photo["url"]).status_code, 403)
        self.assertEqual(self.upload(token).status_code, 403)

    def test_csrf_is_required_for_upload_and_session_creation(self):
        token, _ = self.make_session()
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.staff)
        self.assertEqual(strict.post(f"/api/visits/{self.empty.pk}/upload-sessions/").status_code, 403)
        response = strict.post(f"/api/uploads/{token}/photos/", {"photos": image_file(), "client_ids": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Photo.objects.count(), 0)

    def test_bad_file_leaves_no_photo_or_partial_files(self):
        token, _ = self.make_session()
        response = self.upload(token, [SimpleUploadedFile("fake.png", b"bad")])
        self.assertEqual(response.json()["results"][0]["status"], "error")
        self.assertEqual(Photo.objects.count(), 0)
        self.assertEqual([p for p in Path(self.media.name).rglob("*") if p.is_file()], [])

    def test_database_registration_failure_cleans_published_and_temporary_files(self):
        token, _ = self.make_session()
        with patch("clinic.services.Photo.objects.create", side_effect=OSError("simulated registration failure")):
            with self.assertLogs("clinic.views", level="ERROR"):
                response = self.upload(token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["status"], "error")
        self.assertEqual(Photo.objects.count(), 0)
        self.assertEqual([p for p in Path(self.media.name).rglob("*") if p.is_file()], [])

    @skipUnless(HEIF_SUPPORTED, "HEIF codec is unavailable on this installation")
    def test_real_heic_is_converted_to_web_viewable_jpeg(self):
        output = BytesIO()
        Image.new("RGB", (96, 80), "#356e68").save(output, format="HEIF")
        self.assertEqual(output.getvalue()[4:8], b"ftyp")
        uploaded = SimpleUploadedFile("iphone.heic", output.getvalue(), content_type="image/heic")
        token, _ = self.make_session()
        result = self.upload(token, [uploaded]).json()["results"][0]
        self.assertEqual(result["status"], "saved", result)
        response = self.client.get(result["photo"]["url"])
        self.assertEqual(response["Content-Type"], "image/jpeg")
        with Image.open(BytesIO(response_bytes(response))) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (96, 80))

    def test_missing_heif_codec_reports_actionable_conversion_error(self):
        token, _ = self.make_session()
        fake_heif = SimpleUploadedFile("iphone.heic", b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00", content_type="image/heic")
        with patch("clinic.images.HEIF_SUPPORTED", False):
            result = self.upload(token, [fake_heif]).json()["results"][0]
        self.assertEqual(result["status"], "error")
        self.assertIn("HEIC", result["error"])
        self.assertIn("JPEG", result["error"])
        self.assertEqual(Photo.objects.count(), 0)

    def test_actual_file_format_is_checked_instead_of_extension(self):
        token, _ = self.make_session()
        # A legitimate PNG with an unusual extension can still be decoded safely.
        valid = self.upload(token, [image_file("camera.bin", fmt="PNG")])
        self.assertEqual(valid.json()["results"][0]["status"], "saved")
        # SVG must not become an executable or unvalidated public image.
        svg = SimpleUploadedFile("safe.jpg", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', content_type="image/jpeg")
        invalid = self.upload(token, [svg])
        self.assertEqual(invalid.json()["results"][0]["status"], "error")
        self.assertEqual(Photo.objects.count(), 1)

    def test_size_and_resolution_limits_reject_invalid_images(self):
        token, _ = self.make_session()
        for invalid in [
            image_file(size=(32, 32)),
            image_file(size=(12001, 64)),
            SimpleUploadedFile("large.jpg", b"x" * (20 * 1024 * 1024 + 1), content_type="image/jpeg"),
        ]:
            result = self.upload(token, [invalid]).json()["results"][0]
            self.assertEqual(result["status"], "error")
            self.assertTrue(result["error"])
        self.assertEqual(Photo.objects.count(), 0)

    def test_exif_orientation_applied_and_metadata_stripped(self):
        token, _ = self.make_session()
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = "private location description"
        response = self.upload(token, [image_file(size=(96, 80), exif=exif)])
        photo = response.json()["results"][0]["photo"]
        served = self.client.get(photo["url"])
        with Image.open(BytesIO(response_bytes(served))) as image:
            self.assertEqual(image.size, (80, 96))
            self.assertEqual(dict(image.getexif()), {})
        self.assertIn("no-store", served.get("Cache-Control", ""))

    def test_uncontrolled_private_media_path_is_not_served(self):
        token, _ = self.make_session()
        self.upload(token)
        stored = Photo.objects.get()
        self.assertEqual(self.client.get("/private_media/" + stored.file_key).status_code, 404)
        self.assertEqual(self.client.get("/media/" + stored.file_key).status_code, 404)

    def test_invalid_idempotency_ids_do_not_create_photos(self):
        token, _ = self.make_session()
        response = self.upload(token, client_ids=["not-a-uuid"])
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 200:
            self.assertEqual(response.json()["results"][0]["status"], "error")
        self.assertEqual(Photo.objects.count(), 0)

    def test_missing_batch_metadata_and_oversized_batch_are_rejected(self):
        token, _ = self.make_session()
        missing_ids = self.client.post(
            f"/api/uploads/{token}/photos/", {"photos": image_file()}
        )
        self.assertEqual(missing_ids.status_code, 400)
        too_many = self.upload(token, [image_file(f"{i}.jpg") for i in range(21)])
        self.assertEqual(too_many.status_code, 400)
        self.assertEqual(Photo.objects.count(), 0)

    def test_malformed_visit_json_returns_400(self):
        response = self.client.post(
            f"/api/patients/{self.patient.pk}/visits/", "{broken-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class DemoSeedTests(TestCase):
    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"CLINIC_DEMO_PASSWORD": "local-seed-test-password"})
    def test_seed_is_offline_idempotent_and_has_required_visits(self):
        with tempfile.TemporaryDirectory() as root, override_settings(PRIVATE_MEDIA_ROOT=Path(root)):
            call_command("seed_demo", verbosity=0)
            counts = (Patient.objects.count(), Visit.objects.count(), Photo.objects.count())
            files_before = sorted(str(p.relative_to(root)) for p in Path(root).rglob("*") if p.is_file())
            self.assertGreaterEqual(counts[0], 8)
            representative = Patient.objects.get(chart_number="DEMO-1001")
            self.assertEqual(representative.visits.get(week=1).photos.count(), 4)
            self.assertEqual(representative.visits.get(week=2).photos.count(), 5)
            self.assertEqual(representative.visits.get(week=3).photos.count(), 0)
            self.assertGreaterEqual(Patient.objects.filter(name=representative.name).count(), 2)
            first_sites = set(Photo.objects.filter(visit__patient=representative, visit__week=1).values_list("body_site", flat=True))
            second_sites = set(Photo.objects.filter(visit__patient=representative, visit__week=2).values_list("body_site", flat=True))
            self.assertTrue(first_sites.intersection(second_sites))
            call_command("seed_demo", verbosity=0)
            self.assertEqual(counts, (Patient.objects.count(), Visit.objects.count(), Photo.objects.count()))
            self.assertEqual(files_before, sorted(str(p.relative_to(root)) for p in Path(root).rglob("*") if p.is_file()))
            self.assertTrue(get_user_model().objects.get(username="dlwo8520").check_password("local-seed-test-password"))
