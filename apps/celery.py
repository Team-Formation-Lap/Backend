from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 기본 장고파일 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.settings")
app = Celery("apps")
app.config_from_object("django.conf:settings", namespace="CELERY")

# 등록된 장고 앱 설정에서 task 불러오기
app.autodiscover_tasks()
