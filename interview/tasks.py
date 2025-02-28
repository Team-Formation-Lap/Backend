import os
import boto3
import openai
import fitz
from interview.models import GPTQuestion, Interview, UserAnswer
from dotenv import load_dotenv
import logging
import requests
import uuid
import time

load_dotenv()
openai.api_key=os.getenv("OPENAI_API_KEY")

s3_client = boto3.client('s3',
                         aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                         aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                         region_name=os.getenv('AWS_S3_REGION_NAME'))

# 이력서 PDF에서 텍스트 추출
def extract_text_from_pdf(pdf_path) :
    try:
        response=requests.get(pdf_path)
        response.raise_for_status()

        doc=fitz.open(stream=response.content, filetype="pdf")

        text="\n".join([page.get_text("text") for page in doc])
        return text.strip()

    except requests.exceptions.RequestException as e:
        logging.error(f"PDF 다운로드 실패:{e}")
        return None
    except Exception as e:
        logging.error(f"PDF 텍스트 추출 실패:{e}")
        return None

# 이력서 가져오기
def get_resume_text(interview_id):
    try:
        interview=Interview.objects.get(id=interview_id)
        resume=interview.resume

        if resume is None:
            logging.error(f"면접 ID-{interview_id}에 해당하는 면접이 없음")
            return None

        pdf_path=resume.file_url

    except AttributeError:
        logging.error(f"면접 ID-{interview_id}에 연결된 이력서가 없음")
        return None

    return extract_text_from_pdf(pdf_path)


# gpt 질문 생성
def get_gpt_question(interview_id, user_answer=None):
    # 면접 ID와 사용자 답변을 받아 GPT가 다음 질문을 생성하는 함수
    resume_text = get_resume_text(interview_id)

    #첫 질문일 경우, 사용자의 이력서를 가져와 질문 생성
    if user_answer is None:

        #GPT API 호출하여 첫 질문 생성
        gpt_prompt=f"다음 이력서를 기반으로 면접 첫 번째 질문을 한 개 만들어 주세요:\n{resume_text}"

    else:
        gpt_prompt = f"이전 답변 '{user_answer}'과 이력서를 기반으로 한 다음 질문을 한 개 생성해주세요."

    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 면접관입니다. 면접 질문을 생성하세요."},
                {"role": "user", "content": gpt_prompt}
            ]
        )
        new_question = response.choices[0].message.content

    except Exception as e:
        logging.error(f"GPT API 호출 실패:{e}")
        return None

    tts_url=text_to_speech(new_question, f"interview_{interview_id}")

    if not tts_url:
        logging.error(f"TTS 변환 실패 - 면접 ID : {interview_id}")
        return None

    question=GPTQuestion.objects.create(interview_id=interview_id, content=new_question)

    return {"text":new_question, "audio_url":tts_url}


# TTS - GPT 질문 TTS 변환
def text_to_speech(text, interview_question):
    try:
        response=openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )

        file_path=f"/tmp/{interview_question}.mp3"
        with open(file_path, "wb") as f:
            f.write(response.content)

        timestamp = int(time.time())  # 현재 시간 (초)
        unique_id = uuid.uuid4().hex[:8]  # 짧은 UUID
        s3_key=f"tts/{interview_question}_{timestamp}_{unique_id}.mp3"
        s3_client.upload_file(file_path, os.getenv("AWS_STORAGE_BUCKET_NAME"), s3_key)

        return f"https://{os.getenv('AWS_STORAGE_BUCKET_NAME')}.s3.amazonaws.com/{s3_key}"

    except Exception as e:
        logging.error(f"OpenAI TTS 변환 실패:{e}")
        return None


# STT - 사용자 음성 답변 텍스트로 변환
def speech_to_text(audio_url):
    try:
        response=requests.get(audio_url)
        response.raise_for_status()

        file_path="/tmp/audio.mp3"
        with open(file_path, "wb") as f:
            f.write(response.content)

        client=openai.OpenAI(api_key=os.getenv("OPEN_API_KEY"))

        with open(file_path, "rb") as audio_file:
            transcript=client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        return transcript.text

    except Exception as e:
        logging.error(f"STT 변환 실패:{e}")
        return None


# 사용자 답변 음성 파일 s3 업로드
def upload_audio_to_s3(audio_file, file_name):
    try:
        timestamp = int(time.time())  # 현재 시간 (초)
        unique_id = uuid.uuid4().hex[:8]  # 짧은 UUID
        s3_key = f"stt/{file_name}_{timestamp}_{unique_id}.mp3"
        s3_client.upload_file(audio_file, os.getenv("AWS_STORAGE_BUCKET_NAME"), s3_key)
        return f"https://{os.getenv('AWS_STORAGE_BUCKET_NAME')}.s3.amazonaws.com/{s3_key}"

    except Exception as e:
        logging.error(f"음성 파일 s3 업로드 실패:{e}")
        return None


# 피드백 생성
def generate_feedback(interview_id, behavior_data):
    try:
        interview=Interview.objects.get(id=interview_id)
        questions=GPTQuestion.objects.filter(interview=interview)
        answers=UserAnswer.objects.filter(question__in=questions)

        # if not questions.exists() or not answers.exists():
        #     logging.error(f"면접 ID {interview_id}: 질문 또는 답변이 없음")
        #     return None

        # 면접 질문, 사용자 답변 정리
        conversation = "\n".join({
            f"질문: {q.content}\n답변:{a.content}"
            for q, a in zip(questions,answers)
        })

        # 답변 피드백 생성
        answers_feedback_prompt = f"다음 면접 질문에 대한 사용자의 답변을 보고 각 답변에 대해 피드백을 제공해주세요.\n{conversation}"
        client=openai.OpenAI(api_key=os.getenv("OPENAI_API_KET"))
        answer_feedback_response=client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role":"system", "content":"당신은 면접관입니다. 면접 피드백을 제공합니다."},
                {"role":"user","content":answers_feedback_prompt}
            ]
        )
        answer_feedback= answer_feedback_response.choices[0].message.content.strip()

        # 행동 피드백 생성
        behavior_feedback_prompt=f"다음 면접자의 행동 분석 데이터를 보고 피드백을 제공하세요:\n{behavior_data}"
        behavior_feedback_response=client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role":"system","content":"당신은 면접관입니다. 면접자의 행동에 대해 피드백을 제공합니다."},
                {"role":"user","content":behavior_feedback_prompt}
            ]
        )
        behavior_feedback=behavior_feedback_response.choices[0].message.content.strip()

        # 종합 피드백 생성
        overall_feedback_prompt=f"답변 피드백:{answer_feedback}\n 행동 피드백:{behavior_feedback}\n 이 정보를 바탕으로 면접 전체 피드백을 제공해주세요."
        overall_feedback_response=client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role":"system","content":"당신은 면접관입니다. 면접의 종합적인 평가를 제공합니다."},
                {"role":"user", "content":overall_feedback_prompt}
            ]
        )
        overall_feedback=overall_feedback_response.choices[0].message.content.strip()

        return {
            "overall_feedback": overall_feedback,
            "answer_feedback":answer_feedback,
            "behavior_feedback":behavior_feedback
        }

    except Exception as e:
        logging.error(f"GPT 피드백 생성 실패:{e}")
        return None