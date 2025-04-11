from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from user.authentication import User
from user.serializers import UserSerializer, LoginSerializer, EmailCheckSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
import logging

logger = logging.getLogger(__name__)

class UserRegistrationView(APIView):
    @swagger_auto_schema(request_body=UserSerializer, operation_id="회원가입 API")
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"nickname": user.nickname, "email": user.email}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckEmailDuplicateView(APIView):
    @swagger_auto_schema(request_body=EmailCheckSerializer, operation_id="이메일 중복 확인 API")
    def post(self, request):
        serializer = EmailCheckSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            if User.objects.filter(email=email).exists():
                return Response({"message": "이미 존재하는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "사용 가능한 이메일입니다."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    @swagger_auto_schema(request_body=LoginSerializer, operation_id="로그인 API")
    def post(self, request):
        logger.debug(f"Login attempt with data: {request.data}")
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            logger.debug(f"Attempting to authenticate user: {email}")
            user = authenticate(email=email, password=password)
            
            if user:
                logger.debug(f"User authenticated successfully: {email}")
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'nickname': user.nickname,
                    'email': user.email
                }, status=status.HTTP_200_OK)
            logger.debug(f"Authentication failed for user: {email}")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        logger.debug(f"Serializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
