from django.urls import path
from user import views

appname = "user"

urlpatterns = [path("register", views.UserRegistrationView.as_view(), name="sign-up"),]

path('register', views.UserRegistrationView.as_view(), name='sign-up')