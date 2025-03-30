from django.urls import path
from resume import views

appname = "resume"

urlpatterns = [
    path("upload/<user_id>", views.ResumeUploadView.as_view(), name="upload"),
    path("list/<user_id>", views.ResumeListView.as_view(), name="resumes-list"),
    path("delete/<resume_id>", views.ResumeDeleteView.as_view(), name="delete"),
]