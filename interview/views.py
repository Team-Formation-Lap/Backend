import os
import boto3
import logging
import requests
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from interview.tasks import generate_feedback
from interview.models import Interview, Resume
from result.models import Result
from interview.utils import analyze_behavior
from django.core.exceptions import ObjectDoesNotExist
from interview.serializers import StartInterviewSerializer

s3_client = boto3.client('s3',
                         aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                         aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                         region_name=os.getenv('AWS_S3_REGION_NAME'))

#면접 시작 API
class StartInterviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=StartInterviewSerializer,
        operation_id="면접 시작",
        operation_description="면접을 시작하고 면접방을 생성하는 API",
    )
    def post(self, request):
        try:
            # 요청 데이터에서 질문 개수 가져오기
            questions_count = request.data.get("question_count")
            user_id = request.user.id  # 토큰을 통해 인증된 사용자 ID

            if not questions_count or not (3 <= int(questions_count) <= 10):
                return JsonResponse({"error": "질문 개수는 3~10개 사이여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 사용자의 가장 최근 업로드 된 이력서 가져오기
            resume = Resume.objects.filter(user_id=user_id).order_by("-id").first()

            if not resume:
                return JsonResponse({"error": "이력서를 찾을 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

            interview = Interview.objects.create(user_id=user_id, resume=resume, questions_count=questions_count)

            return JsonResponse(
                {
                    "message": "면접이 시작되었습니다.",
                    "user_id": user_id,
                    "interview_id": interview.id,
                    "resume_id": resume.id,
                    "questions_count": questions_count
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logging.error(f"면접 시작 오류: {e}")
            return JsonResponse({"error": "면접 시작 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 사용자 행동 분석 API
class BehaviorAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="사용자 행동 분석",
        operation_description="면접 영상을 분석하여 행동 데이터를 반환하는 API",
    )
    def post(self, request, interview_id):
        try:
            interview=Interview.objects.get(id=interview_id, user_id=request.user.id)

            # 면접 영상 s3에서 가져오기
            result=Result.objects.filter(interview=interview).first()
            if not result or not result.video_url:
                return Response(
                    {"error": "업로드 된 면접 영상을 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )

            video_url=result.video_url
            video_path=self.download_video_from_s3(video_url, interview_id)
            if not video_path:
                return Response(
                    {"error":"s3에서 영상 다운로드 실패"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # 행동 분석 시작
            behavior_data=analyze_behavior(video_path)

            # 행동 분석 데이터 저장
            result.behavior_data=behavior_data
            result.save()

            os.remove(video_path)
            logging.info(f"로컬 영상 파일 삭제 완료:{video_path}")

            return Response( {
                "message":"행동 분석 완료",
                "behavior_data":behavior_data
            }, status=status.HTTP_201_CREATED)

        except Interview.DoseNotExist:
            return Response(
                {"error":"해당 면접 정보를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(f"행동 분석 오류:{e}")
            return Response({"error":"행동 분석 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


     # s3에서 면접 영상을 다운로드 받아 (백엔드 서버)로컬에 저장 -> 분석 완료 후 로컬 영상 삭제됨
    def download_video_from_s3(self, video_url, interview_id):
        try:
            temp_video_path=f"/tmp/interview_{interview_id}.mp4"
            response=requests.get(video_url)

            if response.status_code !=200:
                return None
            with open(temp_video_path,"wb") as f:
                f.write(response.content)

            return temp_video_path

        except Exception as e:
            logging.error(f"S3 영상 다운로드 실패:{e}")
            return  None


# 면접 결과 생성 API
class InterviewResultView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="면접 결과 생성",
        operation_description="면접 결과를 생성하는 API",
    )
    def post(self, request, interview_id):
        try:
            # 면접 데이터 가져오기
            interview=Interview.objects.get(id=interview_id, user_id=request.user.id)

            # 면접 영상 url 가져오기
            result=Result.objects.filter(interview=interview).first()
            if not result or not result.video_url:
                return Response({"error":"업로드 된 면접 영상을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            #행동 분석 데이터 가져오기
            if result.behavior_data:
                behavior_data=result.behavior_data
            else:
                return Response({"error":"행동 분석 데이터가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            #피드백 생성
            feedback=generate_feedback(interview_id, behavior_data)
            logging.info(f"GPT 피드백 결과:{feedback}")
            if feedback is None:
                return Response({"error":"GPT 피드백 생성 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 피드백 저장
            result.answer_feedback=feedback["answer_feedback"]
            result.behavior_feedback=feedback["behavior_feedback"]
            result.overall_feedback=feedback["overall_feedback"]
            result.save()
            logging.info(f"면접 결과 저장 완료 - Interview ID:{interview_id}")

            return Response({
                "interview_id":interview_id,
                "feedback":{
                    "종합피드백":result.overall_feedback,
                    "행동피드백":result.behavior_feedback,
                    "답변피드백":result.answer_feedback
                },
                "video_url":result.video_url
            }, status=status.HTTP_201_CREATED)

        except ObjectDoesNotExist:
            return Response({"error":"해당 면접을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(f"면접 결과 생성 오류:{e}")
            return Response({"error":"면접 결과 생성 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

