from rest_framework import serializers

class ResultVideoUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        allow_empty_file=False,
        help_text="면접결과 업로드"
    )