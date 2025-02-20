# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from interview.models import Interview, GPTQuestion, UserAnswer
# from asgiref.sync import sync_to_async
# from interview.tasks import get_gpt_question
# import logging
#
# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.interview_id=self.scope['url_route']['kwargs']['interview_id']
#         self.room_group_name=f"interview_{self.interview_id}"
#
#         #그룹 추가
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )
#
#         await self.accept()
#         print(f"WebSocket 연결 성공: 면접 ID {self.interview_id}")
#
#         #GPT 첫 질문 요청
#         await self.start_interview()
#
#
#     async def disconnect(self, close_code):
#         # 웹소켓 연결 종료
#         await  self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )
#         logging.info(f"WebSocket 연결 종료: 면접 ID:{self.interview_id}")
#         print(f"WebSocket 연결 해제 (코드:{close_code})")
#
#     async def receive(self, text_data):
#
#         data=json.loads(text_data)
#         user_answer=data.get("message")
#
#         if not user_answer:
#             return
#
#         question=await sync_to_async(GPTQuestion.objects.filter(interview_id=self.interview_id).last)()
#         answer=await sync_to_async(UserAnswer.objects.create)(question=question, content=user_answer)
#
#         #gpt api 호출(celery 비동기 처리)
#         #get_gpt_question.delay(self.interview_id, user_answer)
#         try:
#             task = get_gpt_question.delay(self.interview_id, None)
#             print(f"✅ Celery Task 실행됨: {task.id}")  # Task 실행 로그 추가
#         except Exception as e:
#             print(f"❌ Celery Task 실행 오류: {e}")  # 에러 로그 추가
#
#     async def send_gpt_question(self, event):
#         #gpt가 생성한 질문을 클라이언트로 전송
#         message=event["message"]
#         await self.send(text_data=json.dumps({"message":message}))
#
#     async def start_interview(self):
#         logging.info(f"🛠 WebSocket -> Celery Task 호출: interview_id={self.interview_id}")
#         result = get_gpt_question.delay(self.interview_id, None)
#         logging.info(f"🎯 Celery Task 전달 결과: {result}")
#
#         #get_gpt_question.delay(self.interview_id, None)