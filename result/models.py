from django.db import models
from interview.models import Interview

class Result(models.Model):
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE)
    overall_feedback = models.TextField(null=True, blank=True)
    behavior_data = models.JSONField(null=True, blank=True)
    behavior_feedback = models.TextField(null=True, blank=True)
    answer_feedback = models.TextField(null=True, blank=True)
    video_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    feedback_summary = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"result: {self.interview.id}"

