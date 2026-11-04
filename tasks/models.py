from django.db import models


class TaskType(models.Model):
    name = models.CharField(max_length=55, unique=True)

    def __str__(self):
        return self.name
