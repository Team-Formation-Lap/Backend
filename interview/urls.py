from django.urls import path
from interview.views import StartInterviewView
from interview.views import InterviewResultView
from interview.views import BehaviorAnalysisView
from interview.views import AnswerSummaryView

app_name='apps'

urlpatterns=[
    path("start", StartInterviewView.as_view(), name="start_interview"),
    path("behavior/<int:interview_id>", BehaviorAnalysisView.as_view(), name="behavior_analysis"),
    path("result/<int:interview_id>", InterviewResultView.as_view(), name="interview_result"),
    path("summary/<int:interview_id>", AnswerSummaryView.as_view(), name="answer_summary"),
]