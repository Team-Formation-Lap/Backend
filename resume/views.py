from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from resume.models import Resume
from resume.serializers import ResumeUploadSerializer
from drf_yasg.utils import swagger_auto_schema
from resume.permission import IsAuthenticatedCustom
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name="dispatch")
class ResumeUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticatedCustom]

    @swagger_auto_schema(
        request_body=ResumeUploadSerializer,
        operation_id="이력서 업로드 API",
    )
    def post(self, request):
        user = request.user

        file = request.FILES.get("file")

        if not file:
            return Response({"error": "파일을 업로드하세요."}, status=status.HTTP_400_BAD_REQUEST)

        if not file.name.endswith('.pdf'):
            return Response({"error": "PDF 파일만 업로드할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        file_path = f"resume/{user.id}/{file.name}"
        saved_path = default_storage.save(file_path, ContentFile(file.read()))
        file_url = default_storage.url(saved_path)

        resume = Resume.objects.create(user=user, filename=file.name, file_url=file_url)

        return Response({
            "message": "이력서 업로드 성공",
            "resume_id": resume.id,
            "filename": resume.filename,
            "file_url": resume.file_url
        }, status=status.HTTP_201_CREATED)
