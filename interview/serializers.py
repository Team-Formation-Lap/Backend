from rest_framework import serializers

class StartInterviewSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text="사용자 ID")
    question_count = serializers.IntegerField(
        min_value=3, max_value=10, help_text="면접 질문 개수 (3~10 사이)"
    )
