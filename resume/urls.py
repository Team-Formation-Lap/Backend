from django.urls import path
from resume import views

appname = "resume"

urlpatterns = [path("upload", views.ResumeUploadView.as_view(), name="upload"),]

path("upload", views.ResumeUploadView.as_view(), name="upload")