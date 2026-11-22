from tasks.models import TaskDependency


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
