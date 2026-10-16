# Django가 시작될 때 Celery 앱을 함께 로드해야 @shared_task가 이 앱에 등록된다.
from .celery import app as celery_app

__all__ = ("celery_app",)
