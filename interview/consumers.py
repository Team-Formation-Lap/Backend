import json
import os
import tempfile
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from interview.tasks import get_gpt_question, speech_to_text, upload_audio_to_s3
from interview.models import GPTQuestion,UserAnswer
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

    # 첫 질문 요청
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

    # 사용자 답변 stt 변환 및 다음 질문 요청
    async def receive(self, text_data=None, bytes_data=None):
        try:
            if bytes_data:
                logging.info("음성 데이터 수신 완료")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                    temp_audio.write(bytes_data)
                    temp_audio_path=temp_audio.name

                logging.info(f"임시 음성 파일 저장:{temp_audio_path}")

                file_name=f"userAnswer"

                s3_url=await database_sync_to_async(upload_audio_to_s3)(temp_audio_path,file_name)

                if not s3_url:
                    logging.error("s3 업로드 실패")
                    return

                user_answer=await database_sync_to_async(speech_to_text)(s3_url)

                if not user_answer:
                    logging.info("STT 변환 실패")
                    return

                logging.info(f"사용자 답변 변환 완료:{user_answer}")

                await self.save_user_answer(user_answer)

                new_question = await database_sync_to_async(get_gpt_question)(self.interview_id, user_answer)

                if new_question:
                    await self.send(text_data=json.dumps({
                        "text": new_question["text"],
                        "audio_url":new_question["audio_url"]
                    }))
                else:
                    await self.send(text_data=json.dumps({"message": "GPT 질문 생성 실패"}))

                os.remove(temp_audio_path)
                logging.info(f"임시 파일 삭제 완료:{temp_audio_path}")

        except Exception as e:
            logging.error(f"WebSocket 메세지 처리 중 오류 발생: {e}")

    @database_sync_to_async
    def save_user_answer(self,user_answer):
        question=GPTQuestion.objects.filter(interview_id=self.interview_id).last()

        if question:
            UserAnswer.objects.create(question=question, content=user_answer)
            logging.info(f"사용자 답변 저장 완료:{user_answer}")
        else:
            logging.error(f"면접 ID{self.interview_id}에 대한 질문을 찾을 수 없음. 답변 저장 실패")