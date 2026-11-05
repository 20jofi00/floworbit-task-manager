from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.conf import settings
from django.core.exceptions import ValidationError

from projects.models import Project


class TaskType(models.Model):
    name = models.CharField(max_length=55, unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=55, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    name = models.CharField(max_length=55)
    description = models.CharField(max_length=455, blank=True)
    task_type = models.ForeignKey(
        TaskType,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="tasks",
        blank=True
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    PRIORITY_CHOICES = [
        ("urgent", "Urgent"),
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]
    deadline = models.DateField()
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES, default="medium")
    is_completed = models.BooleanField(default=False)

    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tasks",
        through="TaskAssignment",
        blank=True,
    )

    def __str__(self):
        return f"{self.name} {self.task_type}, project: {self.project}"


class TaskAssignment(models.Model):
    task = models.ForeignKey(
        Task,
        related_name="task_assignments",
        on_delete=models.CASCADE,
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="task_assignments",
        on_delete=models.PROTECT,
    )
    is_completed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["task", "worker"], name="unique_worker_per_task"
            )
        ]

    def clean(self):
        super().clean()
        if self.task_id and self.worker_id:
            if self.task.project.team.members.filter(pk=self.worker_id).exists():
                return
            else:
                raise ValidationError(
                    {
                     "worker": "This worker is not a member of the project's team"
                    }
                )
