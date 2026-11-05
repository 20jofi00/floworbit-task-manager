from django.core.exceptions import ValidationError

from accounts.models import Worker
from tasks.models import Task, TaskAssignment, TaskDependency


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


def remove_worker_from_task(task: Task, worker: Worker) -> None:
    task_assignment = TaskAssignment.objects.filter(
        task_id=task.id, worker_id=worker.id
    )
    if task_assignment:
        task_assignment.delete()
    else:
        raise ValidationError("This worker is not assigned to this task")


def calculate_task_completion(task: Task) -> bool:
    if TaskAssignment.objects.filter(task_id=task.id):
        tasks_dependency = TaskDependency.objects.filter(dependent_task_id=task.id)
        for task_dependency in tasks_dependency:
            if not task_dependency.prerequisite_task.is_completed:
                return False
        tasks_assignment = TaskAssignment.objects.filter(task_id=task.id)
        for task_assignment in tasks_assignment:
            if not task_assignment.is_completed:
                return False
        return True
    return False
