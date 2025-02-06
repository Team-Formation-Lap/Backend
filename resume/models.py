from django.db import models
from user.models import User

class Resume(models.Model) :
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=500, null=True, blank=True)
    file_url = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self) :
        return f"{self.filename} ({self.user.email})"