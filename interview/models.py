from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from resume.models import Resume
from user.models import User

class Interview(models.Model) :
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE) #on_delete=models.SET_NULL, null=True, blank=True로 하는게 나을지 고민
    questions_count = models.IntegerField(
        validators=[MinValueValidator(3), MaxValueValidator(10)]
    )

    def __str__(self):
        return f"Interview{self.id} | {self.user.email}"


#면접 질문
class GPTQuestion(models.Model):
    interview=models.ForeignKey(Interview, on_delete=models.CASCADE)
    content=models.TextField()

    def __str__(self):
        return f"Question {self.id} - {self.content} | Interview {self.interview}"


#사용자 답변
class UserAnswer(models.Model):
    question=models.OneToOneField(GPTQuestion, on_delete=models.CASCADE)
    content=models.TextField()

    def __str__(self):
        return f"Answer {self.id} - {self.content} | Question {self.question.id}"