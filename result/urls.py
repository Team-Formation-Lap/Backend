from django.urls import path
from result import views

appname = "result"

urlpatterns = [
    path("upload/<int:interview_id>", views.ResultVideoUploadView.as_view(), name="video-upload"),
]