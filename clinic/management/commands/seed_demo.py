"""Create fictional, repeatable data without any downloaded assets."""

import math
import os
import getpass
import random
import uuid
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw, ImageFont

from clinic.models import Patient, Photo, Visit
from clinic.services import store_photo


def sample_image(week, index, site):
    """Draw an explicitly fictional scalp illustration, not a patient photograph."""
    rng = random.Random(f"demo-{week}-{index}")
    image = Image.new("RGB", (1100, 820), "#eceeeb")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    small_font = ImageFont.load_default(size=18)
    draw.rectangle((0, 0, 1100, 68), fill="#203e3c")
    draw.text((32, 23), "FICTIONAL DEMO / GENERATED ILLUSTRATION", fill="white", font=font)
    draw.rounded_rectangle((75, 105, 1025, 726), radius=28, fill="#dfe2de")
    if site == "side":
        center = (545, 390)
        draw.ellipse((325, 160, 760, 645), fill="#d5b69c", outline="#b8967b", width=3)
        draw.ellipse((686, 385, 751, 485), fill="#c9a78a")
        draw.polygon([(700, 280), (780, 380), (708, 398)], fill="#d5b69c")
        draw.rounded_rectangle((405, 570, 620, 698), radius=18, fill="#d5b69c")
    else:
        center = (550, 401 if site == "crown" else 361)
        draw.ellipse((300, 140, 800, 673), fill="#d5b69c", outline="#b8967b", width=3)
    cx, cy = center
    # Sparse deterministic strokes make visits visibly comparable while remaining illustrations.
    for _ in range(1020 + week * 130):
        angle = rng.uniform(0, 2 * math.pi)
        radius = math.sqrt(rng.random())
        x = cx + math.cos(angle) * radius * 220
        y = cy + math.sin(angle) * radius * 229
        if site == "crown" and ((x - cx) ** 2 + (y - cy) ** 2) < (96 - week * 9) ** 2:
            if rng.random() < 0.84:
                continue
        if site == "hairline" and y > cy + 34:
            continue
        if site == "side" and (x > cx + 100 or y > cy + 40):
            continue
        shade = rng.choice(["#453c35", "#615045", "#786252", "#3e3831"])
        length = rng.randint(7, 22)
        draw.line((x, y, x + math.sin(angle) * length, y - length), fill=shade, width=2)
    draw.rectangle((0, 754, 1100, 820), fill="white")
    draw.text((32, 773), f"WEEK {week:02d}  /  IMAGE {index:02d}  /  {site.upper()}", fill="#263b39", font=font)
    draw.text((744, 778), "NO REAL PATIENT DATA", fill="#59615f", font=small_font)
    output = BytesIO()
    image.save(output, "JPEG", quality=90)
    return output.getvalue()


class Command(BaseCommand):
    help = "가상 환자 8명, 방문 기록, 오프라인 샘플 사진과 데모 직원 계정을 생성합니다. 재실행해도 중복되지 않습니다."

    def handle(self, *args, **options):
        account_exists = get_user_model().objects.filter(username="dlwo8520").exists()
        configured_password = os.environ.get("CLINIC_DEMO_PASSWORD", "")
        if not account_exists and not settings.DEBUG and not configured_password:
            raise CommandError(
                "CLINIC_DEMO_PASSWORD must be configured to create a demo account when DJANGO_DEBUG=0. "
                "Set it in the hosting dashboard; do not commit the password to source control."
            )
        if not account_exists and not configured_password:
            configured_password = getpass.getpass("데모 직원 비밀번호: ")
            if not configured_password:
                raise CommandError("데모 직원 비밀번호를 입력해 주세요.")
        user, created = get_user_model().objects.get_or_create(
            username="dlwo8520", defaults={"is_staff": True, "first_name": "데모 직원"}
        )
        if created:
            user.set_password(configured_password)
            user.save()
        elif not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        names = ["김하나", "김하나", "이서준", "박민서", "최지우", "정도윤", "강수빈", "윤서아"]
        patients = []
        for number, name in enumerate(names, start=1001):
            patient, _ = Patient.objects.get_or_create(
                chart_number=f"DEMO-{number}", defaults={"name": name, "is_demo": True}
            )
            patients.append(patient)

        representative = patients[0]
        for week, day in [(1, 5), (2, 12), (3, 19)]:
            Visit.objects.get_or_create(
                demo_key=f"representative-week-{week}",
                defaults={"patient": representative, "week": week, "visited_on": date(2026, 10, day)},
            )
        for number, patient in enumerate(patients[1:], start=1):
            # Two visits in one assigned week exercise visit-date differentiation.
            for repeat in range(2 if number == 1 else 1):
                Visit.objects.get_or_create(
                    demo_key=f"other-{patient.chart_number}-{repeat}",
                    defaults={"patient": patient, "week": 1, "visited_on": date(2026, 10, 6 + number + repeat)},
                )

        created_count = 0
        areas = {
            1: [("정수리", "crown"), ("정수리", "crown"), ("헤어라인", "hairline"), ("측면", "side")],
            2: [("정수리", "crown"), ("정수리", "crown"), ("헤어라인", "hairline"), ("측면", "side"), ("헤어라인", "hairline")],
        }
        for week, sites in areas.items():
            visit = Visit.objects.get(demo_key=f"representative-week-{week}")
            for index, (body_site, drawing_site) in enumerate(sites, start=1):
                demo_key = f"representative-week-{week}-photo-{index}"
                if Photo.objects.filter(demo_key=demo_key).exists():
                    continue
                uploaded = SimpleUploadedFile(
                    f"demo-{week}-{index}.jpg", sample_image(week, index, drawing_site), content_type="image/jpeg"
                )
                _, was_created = store_photo(
                    visit=visit,
                    uploaded_file=uploaded,
                    created_by=user,
                    client_id=uuid.uuid5(uuid.NAMESPACE_URL, f"clinic-demo:{demo_key}"),
                    upload_session=None,
                    demo_key=demo_key,
                    body_site=body_site,
                )
                created_count += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"가상 환자 8명 준비 완료 / 대표 환자 DEMO-1001 / 새 샘플 사진 {created_count}장"
        ))
        self.stdout.write("대표 환자: 1주차 4장 · 2주차 5장 · 3주차 초기 0장")
        self.stdout.write("데모 계정: dlwo8520 / 기존 계정의 비밀번호는 유지됩니다.")
        if created:
            self.stdout.write("입력한 비밀번호로 계정을 만들었습니다. 값은 출력하지 않습니다.")
