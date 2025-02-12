from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from result.models import Result
from result.serializers import ResultVideoUploadSerializer
from drf_yasg.utils import swagger_auto_schema
from result.permission import IsAuthenticatedCustom
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from interview.models import Interview

@method_decorator(csrf_exempt, name="dispatch")
class ResultVideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticatedCustom]

    @swagger_auto_schema(
        request_body=ResultVideoUploadSerializer,
        operation_id="결과 업로드 API",
    )
    def post(self, request, interview_id):
        user = request.user
        video = request.FILES.get("file")

        if not video:
            return Response({"error": "파일을 업로드하세요."}, status=status.HTTP_400_BAD_REQUEST)

        if not video.name.endswith(".webm"):
            return Response({"error": "webm 형식의 영상 파일만 업로드할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        interview = Interview.objects.get(id=interview_id)

        video_path = f"video/{user.id}/{video.name}"
        saved_path = default_storage.save(video_path, ContentFile(video.read()))
        video_url = default_storage.url(saved_path)

        result = Result.objects.create(interview=interview, video_url=video_url)

        return Response({
            "message": "영상 업로드 성공",
            "result_id": result.id,
            "video_url": result.video_url
        }, status=status.HTTP_201_CREATED)