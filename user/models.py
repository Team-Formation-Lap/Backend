from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

#사용자 모델 관리
class CustomUserManager(BaseUserManager):
    def create_user(self, email, nickname, password=None) :
        if not email :
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email) #이메일 소문자로 변환
        user= self.model(email=email, nickname=nickname)
        user.set_password(password)
        return user

    def create_superuser(self, email, nickname, password):
        user=self.create_user(email, nickname, password)
        user.is_staff=True
        user.is_superuser=True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin) :
    email = models.EmailField(max_length=100, unique=True)
    nickname = models.CharField(max_length=200)
    password = models.CharField(max_length=200)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

