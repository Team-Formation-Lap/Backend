import openai
import json
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from interview.models import Interview, GPTQuestion

openai.api_key = "OPENAI_API_KEY"


@shared_task
def get_gpt_question(interview_id, user_answer):
    """GPT API를 호출하여 질문을 생성하고 WebSocket으로 전송"""
    interview = Interview.objects.get(id=interview_id)
    resume_text = interview.resume.resume_file.read().decode("utf-8")  # 이력서 텍스트 가져오기

    # GPT 프롬프트 설정
    messages = [
        {"role": "system", "content": f"이력서를 기반으로 면접 질문을 생성해 주세요.\n\n{resume_text}"},
    ]

    if user_answer:
        messages.append({"role": "user", "content": user_answer})

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )

    gpt_question = response["choices"][0]["message"]["content"]

    # DB에 GPT 질문 저장
    question = GPTQuestion.objects.create(interview_id=interview_id, content=gpt_question)

    # WebSocket으로 질문 전송
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"interview_{interview_id}",
        {
            "type": "send_gpt_question",
            "message": gpt_question}
    )
