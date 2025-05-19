from django.db import models

# Create your models here.

# 
class upload_file(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField()
    
class TwoAQuestions(models.Model):
    doi = models.CharField(max_length=100)
    task_id = models.CharField(max_length=100, default="1")
    source_file = models.FileField()
    question = models.TextField()
    option1 = models.TextField()
    option2 = models.TextField()
    option3 = models.TextField()
    option4 = models.TextField()
    option5 = models.TextField()
    answer_index = models.IntegerField()
    explanation = models.TextField()
    explanation_other1 = models.TextField()
    explanation_other2 = models.TextField()
    explanation_other3 = models.TextField()
    explanation_other4 = models.TextField()
    chosen = models.BooleanField(default=False)