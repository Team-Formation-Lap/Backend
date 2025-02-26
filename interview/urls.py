from django.urls import path
from interview.views import StartInterviewView
from interview.views import InterviewResultView

app_name='apps'

urlpatterns=[
    path("start", StartInterviewView.as_view(), name="start_interview"),
    path("result/<int:interview_id>", InterviewResultView.as_view(), name="interview_result")
]