from django import forms
from django.core.exceptions import ValidationError

from projects.models import Project
from tasks.models import Task, TaskDependency


class TaskModelForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            "name",
            "description",
            "task_type",
            "tags",
            "project",
            "deadline",
            "priority",
        )

    def clean_project(self):
        new_project = self.cleaned_data.get("project")
        if not self.instance.pk or self.instance.project.id == new_project.pk:
            return new_project
        if (
            new_project != self.instance.project
            and not new_project.team.id == self.instance.project.team.id
        ):
            raise ValidationError(
                "A task can only be moved between projects of the same team"
            )
        if (
            TaskDependency.objects.filter(dependent_task_id=self.instance.pk).exists()
            or TaskDependency.objects.filter(
                prerequisite_task_id=self.instance.pk
            ).exists()
        ):
            raise ValidationError(
                "Remove all dependencies involving this task before moving it"
            )

        return new_project


class TaskAdminForm(TaskModelForm):
    pass


class TaskForm(TaskModelForm):

    def __init__(self, *args, **kwargs):
        if "team" not in kwargs:
            raise TypeError("You need to add team")
        self.team = kwargs.pop("team")
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(team=self.team)


class TaskSearchForm(forms.Form):
    name = forms.CharField(
        max_length=55,
        required=False,
        label="",
        widget=forms.TextInput(attrs={"placeholder": "Search by name"}),
    )
