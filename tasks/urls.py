from django.urls import path

from tasks.views import (
    TaskListView,
    TaskDetailView,
    TaskCreateView,
    TaskUpdateView,
    AssignWorkerView,
    RemoveWorkerView,
    AssignmentWorkerView,
    TaskAddDependencyView,
)

app_name = "tasks"

urlpatterns = [
    path("<int:team_pk>/", TaskListView.as_view(), name="task-list"),
    path("<int:team_pk>/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path(
        "<int:team_pk>/<int:pk>/participants/",
        TaskDetailView.as_view(template_name="tasks/task_participants.html"),
        name="task-participants",
    ),
    path(
        "<int:project_pk>/create/",
        TaskCreateView.as_view(),
        name="task-create",
    ),
    path(
        "<int:project_pk>/<int:pk>/update/",
        TaskUpdateView.as_view(),
        name="task-update",
    ),
    path(
        "<int:project_pk>/<int:pk>/add-member/",
        AssignWorkerView.as_view(),
        name="task-add-worker",
    ),
    path(
        "<int:project_pk>/<int:pk>/<int:worker_pk>/remove/",
        RemoveWorkerView.as_view(),
        name="task-remove-worker",
    ),
    path(
        "<int:project_pk>/<int:pk>/task-assignment-status/",
        AssignmentWorkerView.as_view(),
        name="worker-task-state",
    ),
    path(
        "<int:project_pk>/<int:pk>/task-add-dependency/",
        TaskAddDependencyView.as_view(),
        name="task-add-dependency",
    ),
]
