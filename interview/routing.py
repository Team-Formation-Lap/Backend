from django.urls import re_path
from interview.consumers import ChatConsumer  # ✅ ChatConsumer → InterviewConsumer 변경

websocket_urlpatterns = [
    re_path(r"^ws/interview/(?P<interview_id>\d+)/$", ChatConsumer.as_asgi()),
]
