import hashlib
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    name = models.CharField(max_length=80, db_index=True)
    chart_number = models.CharField(max_length=40, unique=True)
    is_demo = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "chart_number"]

    def __str__(self):
        return f"{self.name} · {self.chart_number}"


class Visit(models.Model):
    patient = models.ForeignKey(Patient, related_name="visits", on_delete=models.CASCADE)
    week = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(520)])
    visited_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    demo_key = models.CharField(max_length=80, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["visited_on", "id"]
        indexes = [models.Index(fields=["patient", "visited_on", "id"], name="visit_patient_date")]
        constraints = [models.CheckConstraint(condition=models.Q(week__gte=1, week__lte=520), name="visit_week_range")]

    @property
    def label(self):
        return f"{self.week}주차 · {self.visited_on.month}월 {self.visited_on.day}일"


class UploadSession(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="upload_sessions")
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    @classmethod
    def issue(cls, visit, user):
        token = secrets.token_urlsafe(32)
        session = cls.objects.create(visit=visit, created_by=user, token_hash=cls.hash_token(token),
                                     expires_at=timezone.now() + timedelta(minutes=settings.UPLOAD_SESSION_MINUTES))
        return session, token

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()


class Photo(models.Model):
    visit = models.ForeignKey(Visit, related_name="photos", on_delete=models.CASCADE)
    file_key = models.CharField(max_length=160, unique=True)
    thumbnail_key = models.CharField(max_length=160)
    original_key = models.CharField(max_length=160, blank=True)
    body_site = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    upload_session = models.ForeignKey(UploadSession, null=True, blank=True, on_delete=models.PROTECT)
    client_id = models.UUIDField(default=uuid.uuid4, unique=True)
    demo_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["visit", "created_at", "id"], name="photo_visit_created"),
                   models.Index(fields=["visit", "body_site"], name="photo_visit_site")]
