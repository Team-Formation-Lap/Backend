from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed

class IsAuthenticatedCustom(IsAuthenticated):
    def has_permission(self, request, view):
        if not request.user or request.user.is_anonymous:
            raise AuthenticationFailed("로그인이 필요합니다.")
        return super().has_permission(request, view)