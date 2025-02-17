import logging
from drf_yasg.utils import swagger_auto_schema
from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView
from interview.models import Interview, Resume
from interview.serializers import StartInterviewSerializer


#면접 시작 API
class StartInterviewView(APIView):
    @swagger_auto_schema(
        request_body=StartInterviewSerializer,  # ✅ Serializer를 직접 사용
        operation_id="면접 시작",
        operation_description="면접을 시작하고 면접방을 생성하는 API",
    )
    def post(self, request):

        try:
            #요청 데이터에서 user_id 가져오기
            user_id = request.data.get("user_id")
            #요청 데이터에서 질문 개수 가져오기
            questions_count=request.data.get("question_count")

            if not questions_count or not (3<=int(questions_count)<=10):
                return JsonResponse({"error": "질문 개수는 3~10개 사이여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

            #사용자 이력서 가져오기(우선 임의값 넣어놓음)
            resume=Resume.objects.create(user_id=user_id, file_url="test_resume.pdf")
            if not resume:
                return JsonResponse({"error": "이력서를 찾을 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

            interview=Interview.objects.create(user_id=user_id, resume=resume, questions_count=questions_count)

            return JsonResponse(
                {
                    "message": "면접이 시작되었습니다.",
                    "user_id": user_id,
                    "interview_id":interview.id,
                    "questions_count":questions_count
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logging.error(f"면접 시작 오류{e}")
            return JsonResponse({"error":"면접 시작 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
