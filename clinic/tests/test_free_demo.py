import hashlib
from contextlib import redirect_stdout
from io import BytesIO, StringIO
import os
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from PIL import Image

from clinic.images import process_image
from clinic.models import Patient, Photo, UploadSession, Visit
from clinic.services import store_photo
from config import prepare_runtime


class FreeStorageTests(SimpleTestCase):
    def test_temporary_storage_needs_no_disk_and_repeat_keeps_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / 'clinic'
            with override_settings(DEBUG=False, ON_RENDER=True, STORAGE_MODE='ephemeral',
                                   DATA_DIR=data, PRIVATE_MEDIA_ROOT=data / 'private_media'):
                with patch('config.prepare_runtime.os.path.ismount') as mounted, redirect_stdout(StringIO()):
                    prepare_runtime.main()
                    sample = data / 'private_media' / 'existing.jpg'
                    sample.write_bytes(b'preserve-upload')
                    prepare_runtime.main()
                    mounted.assert_not_called()
                    self.assertEqual(sample.read_bytes(), b'preserve-upload')

    def test_ephemeral_mode_cannot_write_outside_a_dedicated_temp_directory(self):
        with override_settings(DEBUG=False, ON_RENDER=True, STORAGE_MODE='ephemeral',
                               DATA_DIR=Path(__file__).resolve().parent,
                               PRIVATE_MEDIA_ROOT=Path(__file__).resolve().parent / 'private_media'):
            with self.assertRaisesMessage(SystemExit, 'temporary directory'):
                prepare_runtime.main()

    def test_large_camera_photo_keeps_original_and_bounds_display_buffers(self):
        raw = BytesIO()
        Image.new('RGB', (3000, 2000), '#32675f').save(raw, 'JPEG')
        original = raw.getvalue()
        result = process_image(SimpleUploadedFile('camera.jpg', original))
        self.assertEqual(result.original, original)
        self.assertLessEqual(max(result.width, result.height), 2400)
        with Image.open(BytesIO(result.original)) as source:
            self.assertEqual(source.size, (3000, 2000))


@override_settings(DEMO_LOGIN_ENABLED=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FreeDemoTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.storage = override_settings(PRIVATE_MEDIA_ROOT=Path(self.temporary.name))
        self.storage.enable()
        self.addCleanup(self.storage.disable)
        with patch.dict(os.environ, {'CLINIC_DEMO_PASSWORD': ''}), redirect_stdout(StringIO()):
            call_command('seed_demo')
        self.staff = get_user_model().objects.get(username='dlwo8520')

    def test_click_login_keeps_qr_return_url_and_needs_csrf(self):
        client = Client(enforce_csrf_checks=True)
        visit = Visit.objects.get(demo_key='representative-week-3')
        _, token = UploadSession.issue(visit, self.staff)
        target = f'/upload/{token}/'
        response = client.get('/login/', {'next': target})
        self.assertContains(response, '직원으로 접속')
        self.assertNotContains(response, 'name="password"')
        self.assertFalse(self.staff.has_usable_password())
        self.assertEqual(client.post('/login/', {'demo': 'staff', 'next': target}).status_code, 403)
        response = client.post('/login/', {'demo': 'staff', 'next': target},
                               HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, target)
        self.assertEqual(client.get(target).status_code, 200)

    def test_click_cannot_promote_inactive_or_nonstaff_account_or_redirect_offsite(self):
        response = self.client.post('/login/', {'demo': 'staff', 'next': 'https://external.example/'})
        self.assertEqual(response.url, '/patients/')
        self.client.logout()
        for field in ('is_staff', 'is_active'):
            setattr(self.staff, field, False)
            self.staff.save(update_fields=[field])
            self.assertEqual(self.client.post('/login/', {'demo': 'staff'}).status_code, 403)
            setattr(self.staff, field, True)
            self.staff.save(update_fields=[field])
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.post('/login/', {'demo': 'superuser'}).status_code, 403)

    def test_repeated_seed_keeps_week3_upload_and_all_current_image_bytes(self):
        visit = Visit.objects.get(demo_key='representative-week-3')
        image = BytesIO()
        Image.new('RGB', (96, 80), '#234e49').save(image, 'PNG')
        photo, _ = store_photo(visit=visit, uploaded_file=SimpleUploadedFile('new.png', image.getvalue()),
                               created_by=self.staff, client_id=uuid.uuid4())
        root = Path(self.temporary.name)
        def hashes():
            return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob('*') if p.is_file()}
        before = hashes()
        counts = (Patient.objects.count(), Visit.objects.count(), Photo.objects.count())
        with patch.dict(os.environ, {'CLINIC_DEMO_PASSWORD': ''}), redirect_stdout(StringIO()):
            call_command('seed_demo')
            call_command('seed_demo')
        self.assertEqual(before, hashes())
        self.assertEqual(counts, (Patient.objects.count(), Visit.objects.count(), Photo.objects.count()))
        self.assertEqual(list(visit.photos.values_list('pk', flat=True)), [photo.pk])
