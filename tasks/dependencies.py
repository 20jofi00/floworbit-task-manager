from graphlib import CycleError, TopologicalSorter

from django.core.exceptions import ValidationError

from tasks.models import Task, TaskDependency


def has_dependency_path(
    project_id: int,
    start_task_id: int,
    target_task_id: int,
    exclude_dependency_id: int | None = None,
) -> bool:
    links = TaskDependency.objects.filter(
        dependent_task__project_id=project_id,
    )

    if exclude_dependency_id is not None:
        links = links.exclude(pk=exclude_dependency_id)

    prerequisites = {}

    for dependent_id, prerequisite_id in links.values_list(
        "dependent_task_id",
        "prerequisite_task_id",
    ):
        prerequisites.setdefault(dependent_id, []).append(prerequisite_id)

    pending = [start_task_id]
    visited = set()

    while pending:
        task_id = pending.pop()

        if task_id == target_task_id:
            return True

        if task_id in visited:
            continue

        visited.add(task_id)
        pending.extend(prerequisites.get(task_id, []))

    return False


def get_affected_task_order(task: Task) -> list[int]:
    task_ids = set(
        Task.objects.filter(
            project_id=task.project_id,
        ).values_list("pk", flat=True)
    )

    prerequisites = {task_id: set() for task_id in task_ids}
    dependents = {task_id: set() for task_id in task_ids}

    links = TaskDependency.objects.filter(
        dependent_task__project_id=task.project_id,
    )

    for dependent_id, prerequisite_id in links.values_list(
        "dependent_task_id",
        "prerequisite_task_id",
    ):
        if prerequisite_id not in task_ids:
            raise ValidationError(
                "Task dependencies must stay within the same project."
            )

        prerequisites[dependent_id].add(prerequisite_id)
        dependents[prerequisite_id].add(dependent_id)

    affected = set()
    pending = [task.pk]

    while pending:
        task_id = pending.pop()

        if task_id in affected:
            continue

        affected.add(task_id)
        pending.extend(dependents[task_id])

    graph = {task_id: prerequisites[task_id] & affected for task_id in affected}

    try:
        return list(TopologicalSorter(graph).static_order())
    except CycleError:
        raise ValidationError("Task dependencies contain a cycle.")
