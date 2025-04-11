from rest_framework import serializers
from user.models import User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'nickname', 'password']

    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("비밀번호는 6자 이상이어야 합니다.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 존재하는 이메일입니다.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  # 비밀번호 해시
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={"invalid": "이메일 형식을 입력하세요."}
    )