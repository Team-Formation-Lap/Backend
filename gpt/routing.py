from django.urls import path
from gpt.consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/gpt/',ChatConsumer.as_asgi()),
]