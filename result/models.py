from django.db import models
from interview.models import Interview

class Result(models.Model):
    class FeedbackStatus(models.TextChoices):
        PENDING = "PENDING", "대기"          # 작업 발행됨, 워커가 아직 시작 안 함
        PROCESSING = "PROCESSING", "생성 중"  # 워커가 GPT 호출 중
        DONE = "DONE", "완료"
        FAILED = "FAILED", "실패"

    interview = models.OneToOneField(Interview, on_delete=models.CASCADE)
    overall_feedback = models.TextField(null=True, blank=True)
    behavior_data = models.JSONField(null=True, blank=True)
    behavior_feedback = models.TextField(null=True, blank=True)
    answer_feedback = models.TextField(null=True, blank=True)
    video_url = models.TextField(null=True, blank=True)
    feedback_status = models.CharField(
        max_length=20, choices=FeedbackStatus.choices, null=True, blank=True
    )
    feedback_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"result: {self.interview.id}"
