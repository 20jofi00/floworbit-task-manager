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
