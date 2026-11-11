from django import forms
from django.core.exceptions import ValidationError

from projects.models import Project
from tasks.models import Task


class ProjectAdminForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description", "team")

    def clean_team(self):
        new_team = self.cleaned_data.get("team")
        if not self.instance.pk:
            return new_team
        if self.instance.team_id == new_team.pk:
            return new_team
        if Task.objects.filter(
            project_id=self.instance.id
        ).exists():
            raise ValidationError(
                "A project with tasks cannot be moved to another team"
            )

        return new_team


class ProjectSearchForm(forms.Form):
    name = forms.CharField(
        max_length=55,
        required=False,
        label="",
        widget=forms.TextInput(attrs={"placeholder": "Search by name"}),
    )


class TeamProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description")

    def __init__(self, *args, **kwargs):
        if "team" not in kwargs:
            raise TypeError(
                "You need to add team"
            )
        self.team = kwargs.pop("team")
        super().__init__(*args, **kwargs)

    def clean_name(self):
        if self.team.projects.filter(name=self.cleaned_data.get("name")).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Have project with this name")
        return self.cleaned_data.get("name")
