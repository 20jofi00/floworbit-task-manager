from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import Worker
from tasks.models import Task, TaskAssignment
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


def get_team_dashboard_stats(team: Team) -> dict:
    from tasks.services import get_task_display_state

    today = timezone.localdate()
    stats = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "open_tasks": 0,
        "blocked_tasks": 0,
        "overdue_tasks": 0,
    }
    team_tasks = Task.objects.filter(
        project__team=team,
    )

    for task in team_tasks:
        state = get_task_display_state(task=task)
        stats["total_tasks"] += 1
        if task.deadline < today and state != "completed":
            stats["overdue_tasks"] += 1
        if state == "completed":
            stats["completed_tasks"] += 1
        elif state == "blocked":
            stats["blocked_tasks"] += 1
        else:
            stats["open_tasks"] += 1

    projects = []
    for project in team.projects.all():
        tasks = Task.objects.filter(project=project)
        project.total_tasks = tasks.count()
        project.completed_tasks = tasks.filter(is_completed=True).count()
        if project.total_tasks:
            project.progress_percent = round(
                project.completed_tasks / project.total_tasks * 100, 2
            )
        else:
            project.progress_percent = 0
        projects.append(project)

    return {"stats": stats, "projects": projects}
