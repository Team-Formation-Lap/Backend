from django.urls import path
from result import views

appname = "result"

urlpatterns = [
    path("upload/<int:interview_id>", views.ResultVideoUploadView.as_view(), name="video-upload"),
    path("list/<int:user_id>", views.ResultListView.as_view(), name="results-list"),
    path("<int:interview_id>", views.ResultOpenView.as_view(), name="result-open"),
    path("delete/<int:interview_id>", views.ResultDeleteView.as_view(), name="result-delete"),
]