from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from tasks.models import Task, TaskDependency
from tasks.services import get_task_display_state
from teams.models import Team


def get_team_dashboard_stats(team: Team) -> dict:
    today = timezone.localdate()
    stats = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "open_tasks": 0,
        "blocked_tasks": 0,
        "overdue_tasks": 0,
    }

    tasks = Task.objects.filter(project__team=team).prefetch_related(
        "task_assignments",
        Prefetch(
            "dependency_links",
            queryset=TaskDependency.objects.select_related("prerequisite_task"),
        ),
    )

    for task in tasks:
        state = get_task_display_state(task)
        stats["total_tasks"] += 1

        if task.deadline < today and state != "completed":
            stats["overdue_tasks"] += 1

        if state == "completed":
            stats["completed_tasks"] += 1
        elif state == "blocked":
            stats["blocked_tasks"] += 1
        else:
            stats["open_tasks"] += 1

    projects = list(
        team.projects.annotate(
            total_tasks=Count("tasks"),
            completed_tasks=Count(
                "tasks",
                filter=Q(tasks__is_completed=True),
            ),
        ).order_by("pk")
    )

    for project in projects:
        project.progress_percent = (
            round(
                project.completed_tasks / project.total_tasks * 100,
                2,
            )
            if project.total_tasks
            else 0
        )

    return {"stats": stats, "projects": projects}
