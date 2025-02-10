from rest_framework import serializers

class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        allow_empty_file=False,
        help_text="이력서 파일 (PDF)"
    )



