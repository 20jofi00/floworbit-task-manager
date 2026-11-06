from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Worker
from projects.models import Project
from tasks.models import Task, TaskAssignment, TaskDependency
from teams.models import Team


def assign_worker_to_task(task: Task, worker: Worker) -> TaskAssignment:
    team = task.project.team
    if team.members.filter(pk=worker.id).exists():
        task_assignment = TaskAssignment(
            task=task,
            worker=worker,
        )
        task_assignment.save()
        propagate_task_completion(task=task)
        return task_assignment
    else:
        raise ValidationError("Worker is in another team")


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


def refresh_task_completion(task: Task) -> bool:
    task.refresh_from_db()
    task_completion = calculate_task_completion(task=task)
    if task.is_completed != task_completion:
        task.is_completed = task_completion
        task.save()
        return True
    return False


def propagate_task_completion(task: Task) -> None:
    tasks_list = [task]
    while True:
        if not tasks_list:
            break
        if refresh_task_completion(task=tasks_list[0]):
            for task_id_for_check in (
                TaskDependency.objects.filter(
                    prerequisite_task=tasks_list[0].id
                ).values_list("dependent_task", flat=True)
            ):
                tasks_list.append(Task.objects.get(pk=task_id_for_check))
        del tasks_list[0]


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
def add_task_dependency(dependent_task: Task, prerequisite_task: Task) -> None:
    task_dependency = TaskDependency(
        dependent_task=dependent_task,
        prerequisite_task=prerequisite_task,
    )
    task_dependency.save()
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


def remove_worker_from_team(worker: Worker, team: Team) -> None:
    if worker.teams.filter(pk=team.id).exists():
        if TaskAssignment.objects.filter(worker_id=worker.id, task__project__team_id=team.id).exists():
            raise ValidationError("This worker has task in this team")
        team.members.remove(worker)
    else:
        raise ValidationError("This worker is not a member of this team")
