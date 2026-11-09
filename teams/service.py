from django.core.exceptions import ValidationError, PermissionDenied

from accounts.models import Worker
from tasks.models import TaskAssignment
from teams.models import Team


def remove_worker_from_team(worker: Worker, team: Team) -> None:
    if worker.teams.filter(pk=team.id).exists():
        if TaskAssignment.objects.filter(
            worker_id=worker.id, task__project__team_id=team.id
        ).exists():
            raise ValidationError("This worker has task in this team")
        team.members.remove(worker)
    else:
        raise ValidationError("This worker is not a member of this team")


def require_team_member(worker: Worker, team: Team) -> None:
    if not team.members.filter(pk=worker.id).exists():
        raise PermissionDenied("You are not a member of this team")
