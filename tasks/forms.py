from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from projects.models import Project
from tasks.models import Tag, Task, TaskDependency, TaskType
from teams.models import Team


class TaskSearchForm(forms.Form):
    name = forms.CharField(
        max_length=55,
        required=False,
        label="",
        widget=forms.TextInput(attrs={"placeholder": "Search by name"}),
    )


class TaskFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        if "team" not in kwargs:
            raise TypeError("You need to add team")
        self.team = kwargs.pop("team")

        super().__init__(*args, **kwargs)
        self.fields["projects"].queryset = Project.objects.filter(
            team=self.team,
        )
        self.fields["task_types"].queryset = TaskType.objects.filter(
            tasks__project__team=self.team
        ).distinct()
        self.fields["task_tags"].queryset = Tag.objects.filter(
            tasks__project__team=self.team
        ).distinct()

    name = forms.CharField(
        max_length=55,
        required=False,
        label="",
        widget=forms.TextInput(attrs={"placeholder": "Search by name"}),
    )
    projects = forms.ModelMultipleChoiceField(
        required=False,
        queryset=None,
    )
    task_types = forms.ModelMultipleChoiceField(
        required=False,
        queryset=None,
    )
    task_tags = forms.ModelMultipleChoiceField(
        required=False,
        queryset=None,
    )

    priority = forms.ChoiceField(
        required=False,
        choices=[("", "Any priority")] + Task.PRIORITY_CHOICES,
    )
    deadline_before = forms.DateField(
        required=False,
        label="Due by",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


class TeamTaskForm(TaskSearchForm):
    def __init__(self, *args, **kwargs):
        if "user" not in kwargs:
            raise TypeError("You need to add user")
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["teams"].queryset = Team.objects.filter(members=self.user)

    teams = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
    )


class TaskModelForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            "name",
            "description",
            "task_type",
            "tags",
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


class TaskForm(TaskModelForm):
    pass


class TaskUpdateForm(TaskModelForm):
    class Meta:
        model = Task
        fields = TaskModelForm.Meta.fields + ("project",)

    def __init__(self, *args, **kwargs):
        if "project" not in kwargs:
            raise TypeError("You need to add project")
        self.project = kwargs.pop("project")
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(team=self.project.team)


class TaskAdminForm(TaskModelForm):
    class Meta:
        model = Task
        fields = TaskModelForm.Meta.fields + ("project",)


class AssignWorkerForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if "team" not in kwargs:
            raise TypeError("You need to add team")
        self.team = kwargs.pop("team")
        super().__init__(*args, **kwargs)
        self.fields["worker"].queryset = get_user_model().objects.filter(
            teams=self.team
        )

    worker = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label="",
    )


class TaskAddDependencyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if "project" not in kwargs:
            raise TypeError("You need to add project")
        self.project = kwargs.pop("project")
        if "task" not in kwargs:
            raise TypeError("You need to add task")
        self.task = kwargs.pop("task")
        super().__init__(*args, **kwargs)
        self.fields["prerequisite_task"].queryset = Task.objects.filter(
            project=self.project,
        ).exclude(pk=self.task.id)

    prerequisite_task = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label="",
    )
