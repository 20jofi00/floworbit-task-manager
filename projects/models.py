from django.db import models
from django.db.models import UniqueConstraint

from teams.models import Team


class Project(models.Model):
    name = models.CharField(max_length=55)
    description = models.CharField(max_length=455, blank=True)
    team = models.ForeignKey(Team, related_name="projects", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["team", "name"], name="unique_project_name_per_team"
            )
        ]

    def __str__(self):
        return self.name
