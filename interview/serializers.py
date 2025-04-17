from rest_framework import serializers

class StartInterviewSerializer(serializers.Serializer):
    question_count = serializers.IntegerField(
        min_value=3, max_value=10, help_text="면접 질문 개수 (3~10 사이)"
    )
    resume_id = serializers.IntegerField(required=False)
