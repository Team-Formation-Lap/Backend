from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from user import serializers

class UserRegistrationView(APIView):
    @swagger_auto_schema(request_body=serializers.UserSerializer,
                         operation_id="회원가입 API")
    def post(self, request):
        serializer = serializers.UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"nickname": user.nickname, "email": user.email}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckEmailDuplicateView(APIView):
    @swagger_auto_schema(request_body=serializers.EmailCheckSerializer,
                         operation_id="이메일 중복 확인 API")
    def post(self, request):
        serializer = serializers.EmailCheckSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            if serializers.User.objects.filter(email=email).exists():
                return Response({"message": "이미 존재하는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "사용 가능한 이메일입니다."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)