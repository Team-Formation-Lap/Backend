from django.urls import path
from resume import views

appname = "resume"

urlpatterns = [
    path("upload/<user_id>", views.ResumeUploadView.as_view(), name="upload"),
    path("delete/<resume_id>", views.ResumeDeleteView.as_view(), name="delete"),
]