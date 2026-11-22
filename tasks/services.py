from django.core.exceptions import ValidationError
from django.db import transaction

from tasks.dependencies import get_affected_task_order
from accounts.models import Worker
from tasks.models import Task, TaskAssignment, TaskDependency


@transaction.atomic
def assign_worker_to_task(task: Task, worker: Worker) -> TaskAssignment:
    assignment = TaskAssignment(
        task=task,
        worker=worker,
    )
    assignment.full_clean()
    assignment.save()

    propagate_task_completion(task=task)

    return assignment


def remove_worker_from_task(task: Task, worker: Worker) -> None:
    task_assignment = TaskAssignment.objects.filter(
        task_id=task.id, worker_id=worker.id
    )
    if task_assignment:
        task_assignment.delete()
        propagate_task_completion(task=task)
    else:
        raise ValidationError("This worker is not assigned to this task")


def calculate_task_completion(task: Task) -> bool:
    assignments = TaskAssignment.objects.filter(task_id=task.pk)
    if not assignments.exists() or assignments.filter(is_completed=False).exists():
        return False
    return not TaskDependency.objects.filter(
        dependent_task_id=task.pk,
        prerequisite_task__is_completed=False,
    ).exists()


def refresh_task_completion(task: Task) -> bool:
    task.refresh_from_db()
    task_completion = calculate_task_completion(task=task)
    if task.is_completed != task_completion:
        task.is_completed = task_completion
        task.save(update_fields=["is_completed"])
        return True
    return False


@transaction.atomic
def propagate_task_completion(task: Task) -> None:
    order = get_affected_task_order(task)
    tasks = Task.objects.in_bulk(order)

    for task_id in order:
        refresh_task_completion(task=tasks[task_id])


def set_assignment_completion(worker: Worker, task: Task, is_completed: bool) -> None:
    try:
        task_assignment = TaskAssignment.objects.get(
            task_id=task.id, worker_id=worker.id
        )
        task_assignment.is_completed = is_completed
        task_assignment.save()
        propagate_task_completion(task=task)
    except TaskAssignment.DoesNotExist:
        raise ValidationError("This worker is not assigned to this task")


@transaction.atomic
def add_task_dependency(
    dependent_task: Task,
    prerequisite_task: Task,
) -> None:
    dependency = TaskDependency(
        dependent_task=dependent_task,
        prerequisite_task=prerequisite_task,
    )
    dependency.full_clean()
    dependency.save()

    propagate_task_completion(task=dependent_task)


@transaction.atomic
def delete_task_dependency(dependent_task: Task, prerequisite_task: Task) -> None:
    task_dependency = TaskDependency.objects.filter(
        dependent_task=dependent_task, prerequisite_task=prerequisite_task
    )
    if task_dependency:
        task_dependency.delete()
        propagate_task_completion(task=dependent_task)
    else:
        raise ValidationError("This task dependency does not exist")


def get_task_display_state(task: Task) -> str:
    dependencies = task.dependency_links.all()
    for task_dependency in dependencies:
        if not task_dependency.prerequisite_task.is_completed:
            return "blocked"
    if task.is_completed:
        return "completed"
    if task.task_assignments.exists():
        return "in_progress"
    return "unassigned"
