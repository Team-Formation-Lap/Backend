from django.urls import path
from interview.views import StartInterviewView

app_name='apps'

urlpatterns=[
    path("start", StartInterviewView.as_view(), name="start_interview")
]