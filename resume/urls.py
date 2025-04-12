from django.urls import path
from resume import views

appname = "resume"

urlpatterns = [
    path("upload/", views.ResumeUploadView.as_view(), name="upload"),
    path("list/", views.ResumeListView.as_view(), name="resumes-list"),
    path("delete/<int:resume_id>", views.ResumeDeleteView.as_view(), name="delete"),
]