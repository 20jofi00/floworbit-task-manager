from django import forms
from django.core.exceptions import ValidationError

from tasks.models import Task, TaskDependency


class TaskAdminForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("name", "description", "task_type", "tags", "project", "deadline", "priority")

    def clean_project(self):
        new_project = self.cleaned_data.get("project")
        if not self.instance.pk or self.instance.project_id == new_project.pk:
            return new_project
        if not new_project.team.id == self.instance.project.team.id:
            raise ValidationError(
                "A task can only be moved between projects of the same team"
            )
        if TaskDependency.objects.filter(
            dependent_task_id=self.instance.pk
        ).exists() or TaskDependency.objects.filter(
            prerequisite_task_id=self.instance.pk
        ).exists():
            raise ValidationError(
                "Remove all dependencies involving this task before moving it"
            )

        return new_project
