from django.urls import path
from user import views

appname = "user"

urlpatterns = [
    path("register", views.UserRegistrationView.as_view(), name="sign-up"),
    path("login", views.LoginView.as_view(), name="login"),
    path("exists", views.CheckEmailDuplicateView.as_view(), name="check-email"),
]

# path("register", views.UserRegistrationView.as_view(), name="sign-up")
