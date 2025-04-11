from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from result.models import Result
from result.serializers import ResultVideoUploadSerializer
from drf_yasg.utils import swagger_auto_schema
from interview.models import Interview, GPTQuestion, UserAnswer

class ResultVideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ResultVideoUploadSerializer,
        operation_id="면접 영상 업로드",
        operation_description="면접 영상을 s3에 업로드 하는 API",
    )
    def post(self, request, interview_id):
        video = request.FILES.get("file")

        if not video:
            return Response({"error": "파일을 업로드하세요."}, status=status.HTTP_400_BAD_REQUEST)

        if not video.name.endswith((".webm")):
            return Response({"error": "webm 형식의 영상 파일만 업로드할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        interview = Interview.objects.get(id=interview_id, user_id=request.user.id)
        user_id = request.user.id

        video_path = f"video/{user_id}/{interview_id}/{video.name}"
        saved_path = default_storage.save(video_path, ContentFile(video.read()))
        video_url = default_storage.url(saved_path)

        result = Result.objects.create(interview=interview, video_url=video_url)

        return Response({
            "message": "영상 업로드 성공",
            "result_id": result.id,
            "video_url": result.video_url
        }, status=status.HTTP_201_CREATED)

class ResultListView(APIView):
    @swagger_auto_schema(
        operation_id="면접결과 조회",
        operation_description="면접결과 리스트를 조회하는 API"
    )
    def get(self, request, user_id):
        results = Result.objects.filter(interview_id__user_id=user_id)
        result_list = [
            {
                "result_id": result.id
            }
            for result in results
        ]
        return Response({"results": result_list}, status=status.HTTP_200_OK)

class ResultOpenView(APIView):
    @swagger_auto_schema(
        operation_id="면접결과 내용 조회",
        operation_description="면접결과 내용을 출력하는 API"
    )
    def get(self, request, interview_id):
        result = Result.objects.get(interview_id=interview_id)

        questions = GPTQuestion.objects.filter(interview_id=interview_id).prefetch_related("useranswer")
        qna_pair = []
        for q in questions:
            qna_pair.append({
                "question": q.content,
                "answer": q.useranswer.content if hasattr(q, "useranswer") else " "
            })

        return Response({
            "resume": result.interview.resume.filename,
            "resume_id": result.interview.resume_id,
            "overall_feedback": result.overall_feedback,
            "behavior_feedback": result.behavior_feedback,
            "answer_feedback": result.answer_feedback,
            "qna_pair": qna_pair,
        }, status=status.HTTP_200_OK)
