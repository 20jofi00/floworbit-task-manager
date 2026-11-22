from django.core.exceptions import ValidationError

from projects.models import Project
from teams.models import Team


def move_project_to_team(team: Team, project: Project) -> None:
    if project.tasks.exists():
        raise ValidationError("A project with tasks cannot be moved to another team")
    if project.team.id == team.id:
        raise ValidationError("This project already belongs to this team")
    if team.projects.filter(name=project.name).exists():
        raise ValidationError("This team already has a project with this name")
    project.team = team
    project.save()
