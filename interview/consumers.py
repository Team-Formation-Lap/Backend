import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from interview.tasks import get_gpt_question
import logging

class ChatConsumer(AsyncWebsocketConsumer):

    # 웹소켓 연결
    async def connect(self):
        self.interview_id=self.scope['url_route']['kwargs']['interview_id']
        self.room_group_name=f"interview_{self.interview_id}"

        #그룹 추가
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f"WebSocket 연결 성공: 면접 ID - {self.interview_id}")

        #GPT 첫 질문 요청
        await self.start_interview()

    # 웹소켓 연결 종료
    async def disconnect(self, close_code):

        await  self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logging.info(f"WebSocket 연결 종료: 면접 ID - {self.interview_id}")
        print(f"WebSocket 연결 해제 (코드:{close_code})")


    async def start_interview(self):
        logging.info(f"WebSocket -> GPT 첫 질문 요청: interview_id={self.interview_id}")

        first_question = await database_sync_to_async(get_gpt_question)(self.interview_id, None)
        print(f"First question:{first_question}")

        if first_question:
            await self.send(text_data=json.dumps({
                "text": first_question["text"],
                "audio_url":first_question["audio_url"]

            }))
        else:
            await self.send(text_data=json.dumps({"message":"이력서를 찾을 수 없습니다."}))

    async def receive(self, text_data):
        try:
            data=json.loads(text_data)
            user_audio_url=data.get("audio_url")

            if not user_audio_url:
                logging.warning("사용자 음성 파일이 없음")
                return

            new_question = await database_sync_to_async(get_gpt_question)(self.interview_id, user_audio_url)

            if new_question:
                await self.send(text_data=json.dumps({
                    "text": new_question["text"],
                    "audio_url":new_question["audio_url"]
                }))
            else:
                await self.send(text_data=json.dumps({"message": "GPT 질문 생성 실패"}))

        except json.JSONDecodeError:
            logging.error("JSON 디코딩 오류 발생")
        except Exception as e:
            logging.error(f"WebSocket 메세지 처리 중 오류 발생: {e}")