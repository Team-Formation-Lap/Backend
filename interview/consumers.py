import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("WebSocket 연결 성공")

    async def disconnect(self, close_code):
        print(f"WebSocket 연결 해제 (코드:{close_code})")

    async def receive(self, text_data):
        print(f"수신된 메시지:{text_data}")
        await self.send(text_data=json.dumps({"message":"메시지를 받았습니다."}))