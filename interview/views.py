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
from django.db import transaction
from django.db.models import Q
from interview.tasks import generate_feedback_task
from interview.models import Interview, Resume, UserAnswer
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
            user_id = request.user.id  # 토큰을 통해 인증된 사용자 ID
            data=request.data
            questions_count = request.data.get("question_count")
            resume_id=data.get("resume_id")

            if not questions_count or not (3 <= int(questions_count) <= 10):
                return JsonResponse({"error": "질문 개수는 3~10개 사이여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

            if resume_id:
                try:
                    resume = Resume.objects.get(id=resume_id, user_id=user_id) #기존 이력서 사용
                except Resume.DoesNotExist:
                    return JsonResponse({"error": "지정한 이력서를 찾을 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                resume = Resume.objects.filter(user_id=user_id).order_by("-id").first()  #새로운 이력서 업로
                if not resume:
                    return JsonResponse({"error": "이력서를 찾을 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

            interview=Interview.objects.create(user_id=user_id,resume=resume,questions_count=questions_count)

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

        except Exception as e:(
        logging.error(f"면접 시작 오류: {e}"))
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

        except Interview.DoesNotExist:
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
# POST: 피드백 생성 작업을 큐에 넣고 바로 202를 반환한다. (GPT 호출을 요청 안에서 기다리지 않음)
# GET : 생성 상태를 조회한다. 완료되면 피드백을 함께 반환한다.
class InterviewResultView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="면접 결과 생성",
        operation_description="면접 결과(피드백) 생성 작업을 시작하는 API. 202를 반환하며, 결과는 GET으로 조회한다.",
    )
    def post(self, request, interview_id):
        try:
            interview = Interview.objects.get(id=interview_id, user_id=request.user.id)

            result = Result.objects.filter(interview=interview).first()
            if not result or not result.video_url:
                return Response({"error":"업로드 된 면접 영상을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            if not result.behavior_data:
                return Response({"error":"행동 분석 데이터가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            Status = Result.FeedbackStatus

            # 이미 완료된 결과면 다시 만들지 않고 그대로 반환 (재요청에 멱등)
            if result.feedback_status == Status.DONE:
                return Response(self._body(interview_id, result), status=status.HTTP_200_OK)

            # 처음 요청이거나 이전 작업이 실패한 경우에만 PENDING으로 바꾸고 작업을 발행한다.
            # 조건부 UPDATE라 동시에 두 번 요청해도 작업은 한 번만 발행된다.
            with transaction.atomic():
                queued = Result.objects.filter(
                    Q(feedback_status__isnull=True) | Q(feedback_status=Status.FAILED),
                    id=result.id,
                ).update(feedback_status=Status.PENDING, feedback_error=None)

                if queued == 1:
                    # 커밋된 뒤에 발행해야 워커가 PENDING 상태를 읽을 수 있다.
                    result_id = result.id
                    transaction.on_commit(lambda: generate_feedback_task.delay(result_id))

            result.refresh_from_db(fields=["feedback_status"])
            return Response(self._body(interview_id, result), status=status.HTTP_202_ACCEPTED)

        except ObjectDoesNotExist:
            return Response({"error":"해당 면접을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(f"면접 결과 생성 요청 오류:{e}")
            return Response({"error":"면접 결과 생성 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_id="면접 결과 생성 상태 조회",
        operation_description="피드백 생성 상태(PENDING, PROCESSING, DONE, FAILED)를 조회하는 API. DONE이면 피드백을 함께 반환한다.",
    )
    def get(self, request, interview_id):
        try:
            interview = Interview.objects.get(id=interview_id, user_id=request.user.id)
            result = Result.objects.filter(interview=interview).first()
            if not result or not result.feedback_status:
                return Response({"error":"생성 요청된 면접 결과가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
            return Response(self._body(interview_id, result), status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error":"해당 면접을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def _body(interview_id, result):
        body = {"interview_id": interview_id, "status": result.feedback_status}
        if result.feedback_status == Result.FeedbackStatus.DONE:
            body["feedback"] = {
                "종합피드백": result.overall_feedback,
                "행동피드백": result.behavior_feedback,
                "답변피드백": result.answer_feedback,
            }
            body["video_url"] = result.video_url
        elif result.feedback_status == Result.FeedbackStatus.FAILED:
            body["error"] = result.feedback_error
        return body
