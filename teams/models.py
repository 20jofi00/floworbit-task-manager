from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=155, unique=True)
    description = models.CharField(max_length=255, blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="teams"
    )

    def __str__(self):
        return self.name
