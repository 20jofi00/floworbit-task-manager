from django.core.exceptions import ValidationError

from accounts.models import Worker
from projects.models import Project
from teams.models import Team
from teams.service import require_team_member


def move_project_to_team(team: Team, project: Project) -> None:
    if project.tasks.exists():
        raise ValidationError("A project with tasks cannot be moved to another team")
    if project.team.id == team.id:
        raise ValidationError("This project already belongs to this team")
    if team.projects.filter(name=project.name).exists():
        raise ValidationError("This team already has a project with this name")
    project.team = team
    project.save()


def require_project_access(worker: Worker, project: Project) -> None:
    require_team_member(
        worker=worker, team=project.team
    )
