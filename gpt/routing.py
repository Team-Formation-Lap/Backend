from django.urls import re_path
from gpt.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"^ws/gpt/?$",ChatConsumer.as_asgi()),
]