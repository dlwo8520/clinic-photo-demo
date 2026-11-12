from django.urls import path
from . import views

urlpatterns = [
    path("healthz/", views.health, name="health"),
    path("", views.home, name="home"),
    path("patients/", views.patients, name="patients"),
    path("patients/<int:patient_id>/", views.compare, name="compare"),
    path("api/patients/<int:patient_id>/visits/", views.create_visit, name="create_visit"),
    path("api/visits/<int:visit_id>/photos/", views.visit_photos, name="visit_photos"),
    path("api/visits/<int:visit_id>/upload-sessions/", views.issue_upload_session, name="issue_upload_session"),
    path("upload/<str:token>/", views.upload_page, name="upload"),
    path("api/upload-sessions/<str:token>/qr/", views.qr_image, name="qr"),
    path("api/uploads/<str:token>/photos/", views.upload_photos, name="upload_photos"),
    path("photos/<int:photo_id>/image/", views.photo_file, name="photo"),
    path("photos/<int:photo_id>/thumbnail/", views.photo_file, {"thumbnail": True}, name="thumbnail"),
]
