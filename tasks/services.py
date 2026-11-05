from django.core.exceptions import ValidationError

from accounts.models import Worker
from tasks.models import Task, TaskAssignment


def assign_worker_to_task(task: Task, worker: Worker) -> TaskAssignment:
    team = task.project.team
    if team.members.filter(pk=worker.id).exists():
        task_assignment = TaskAssignment(
            task=task,
            worker=worker,
        )
        task_assignment.save()
        return task_assignment
    else:
        raise ValidationError("Worker is in another team")
