from django.urls import path
from resume import views

appname = "resume"

urlpatterns = [path("upload/<user_id>", views.ResumeUploadView.as_view(), name="upload"),]