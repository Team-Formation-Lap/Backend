from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from user.serializers import UserSerializer

class UserRegistrationView(APIView):
    @swagger_auto_schema(request_body=UserSerializer,
                         operation_id="회원가입 API")
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"nickname": user.nickname, "email": user.email}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
