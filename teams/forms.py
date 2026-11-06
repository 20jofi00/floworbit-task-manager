from django import forms

from tasks.models import TaskAssignment
from teams.models import Team


class TeamAdminForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ("name", "description", "members")

    def clean_members(self):
        new_members = self.cleaned_data.get("members")
        if not self.instance.pk:
            return new_members

        old_members_ids = set(self.instance.members.values_list("id", flat=True))
        new_members_list = set(
            new_members.values_list("id", flat=True)
        ) if new_members else set()

        removed_members = old_members_ids - new_members_list
        if removed_members:
            if TaskAssignment.objects.filter(
                task__project__team=self.instance,
                worker_id__in=removed_members
            ).exists():
                raise forms.ValidationError(
                    "Remove this worker from the team's tasks before removing them from the team"
                )
        return new_members
