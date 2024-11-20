from django.db import models

class UploadedFile(models.Model):
    file = models.FileField(upload_to="uploaded_files/")
    embedding_path = models.CharField(max_length=255, blank=True, null=True)
    embedding_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
