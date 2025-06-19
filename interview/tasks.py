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

QUESTION_GUIDELINE_INIT = (
    f"현재 면접상황이고, 당신은 지원자를 평가하는 기술면접관 역할이다.\n"
    f"기술면접 기준에 따라 유동적인 질문을 생성할 것\n"
    f"질문은 실제 기술면접처럼 맥락 있고 유연하게 구성하되, 기준의 핵심 평가 요소를 반영해야 한다.\n"
    f"0.논리성: 문제를 단계적으로 분석하고 해결하는 논리적 사고 능력\n" 
    f"기준에 대해 언급은 하지말고 짧은 인사로 시작\n"
    f"**면접 대사 외에는 말하지 말 것**\n"
    f"**질문은 반드시 하나만, 실제 면접 질문처럼 말할 것. 설명이나 해설 없이 질문만 생성**\n"
)
QUESTION_GUIDELINE_FOLLOWING = (
    f"이전 답변내용과 이력서를 반영한 유동적인 면접질문을 하나씩 생성할 것\n"
    f"0.논리성: 문제를 단계적으로 분석하고 해결하는 논리적 사고 능력\n"
    f"1.정확성: 기술적 지식의 정확성, 구현 결과물의 신뢰성\n"
    f"2.효율성: 성능, 확장성, 코드 최적화 등 효율적인 해결책 제시\n"
    f"3.협업 및 커뮤니케이션: 협업 경험, 코드 리뷰 태도, 의사소통 능력\n"
    f"4.성장 가능성 및 태도: 새로운 기술 학습 의지, 피드백 수용, 문제 접근 태도\n"
    f"**질문은 반드시 하나만, 실제 면접 질문처럼 말할 것. 설명이나 해설 없이 질문만 생성**\n"
    f"질문은 100자를 넘기지 말 것"
)

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
    resume_text = get_resume_text(interview_id)

    interview = Interview.objects.get(id=interview_id)
    question_count = interview.user.question_count

    if user_answer is None:
        gpt_prompt = (f"이력서: {resume_text}\n"
                      f"가이드라인: {QUESTION_GUIDELINE_INIT}\n"
                      )
    else :
        gpt_prompt = (f"사용자 답변: {user_answer}\n"
                      f"이력서: {resume_text}\n"
                      f"{question_count}번 기준에 대해 질문할 것"
                      f"가이드라인: {QUESTION_GUIDELINE_FOLLOWING}\n"
                     )

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

    user = interview.user
    user.question_count += 1
    if user.question_count == 5 :
        user.question_count = 0
    user.save()

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

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        answer_feedback_list = []

        #답변별 피드백 생성
        for answer in answers:
            question = answer.question
            prompt = (
                f"당신은 전문 면접 컨설턴트입니다.\n"
                f"아래는 면접 질문과 사용자의 답변입니다.\n"
                f"질문: {question.content}\n"
                f"답변: {answer.content}\n\n"
                f"아래 3가지 기준에 따라 피드백을 **한단락으로** 제공해주세요:\n"
                f"1. 사용자의 답변 중 기술적으로 틀린 부분이 있다면 **어느 문장의 어떤 내용이 왜 잘못되었는지**를 명확히 설명해주세요.\n"
                f"올바른 개념이나 용어로 **정정된 내용**을 함께 제시해주세요.\n"
                f"해당 오류에 대해 사용자가 보완하면 좋을 공부 방향(예: 문서, 키워드, 관련 주제 등)을 피드백을 제공해주세요."
                f"2.면접 상황에서 이 답변이 얼마나 명확하고 설득력 있게 전달되었는지 평가해주세요\n"
                f"중복 표현, 모호한 단어, 불필요하게 긴 문장이 있는 경우, 어떻게 더 간결하고 논리적으로 표현할 수 있는지도 제안해주세요.\n"
                f"질문에 적절히 답변했는지, 논리 구조가 명확했는지를 평가해주세요.\n"
                f"3. 도입 → 문제 인식 → 해결 → 결과의 흐름이 자연스러운지, 면접관 입장에서 신뢰를 줄 수 있는 구성인지 판단해주세요.\n"
                #f"출력은 다음 형식을 따르세요: \"question\": \"질문 내용\",\"answer\": \"답변 내용\",\"feedback\": \"답변피드백\""
            )


            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 면접관입니다. 피드백을 제공합니다."},
                    {"role": "user", "content": prompt}
                ]
            )
            feedback = response.choices[0].message.content.strip()
            answer.feedback = feedback
            answer.save()

            answer_feedback_list.append({
                "question": question.content,
                "answer": answer.content,
                "feedback": feedback
            })

        # 행동 피드백 생성
        behavior_feedback_prompt=(f"당신은 전문 면접 컨설턴트입니다. 아래는 사용자의 모의면접 영상에서 추출된 행동 데이터입니다. "
                                  f"각 행동(event)은 면접자가 특정 시간 동안 보인 행동을 의미합니다."
                                  f"각 행동에 대해 면접 전문가로서 2~4문장의 피드백을 작성해 주세요."
                                  f"다음 3가지를 포함하여 작성해 주세요:1. 이 행동이 어떤 인상을 줄 수 있는지, 2. 면접에서 바람직한 행동인지 평가,3. 실전 면접에서 개선/유지할 팁"
                                  f"출력은 다음 형식을 따르세요: [시작~끝초|피드백]"
                                  f"행동 데이터:{behavior_data}")

        behavior_feedback_response=client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role":"system","content":"당신은 면접관입니다. 면접자의 행동에 대해 피드백을 제공합니다."},
                {"role":"user","content":behavior_feedback_prompt}
            ]
        )
        behavior_feedback=behavior_feedback_response.choices[0].message.content.strip()

        # 종합 피드백 생성
        overall_feedback_prompt=f"답변 피드백:{answer_feedback_list}\n 행동 피드백:{behavior_feedback}\n 이 정보를 바탕으로 면접 전체 피드백을 제공해주세요."
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
            "answer_feedback":answer_feedback_list,
            "behavior_feedback":behavior_feedback
        }

    except Exception as e:
        logging.error(f"GPT 피드백 생성 실패:{e}")
        return None