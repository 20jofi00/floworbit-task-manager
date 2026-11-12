from django.urls import path

from tasks.views import TaskListView, TaskDetailView, TaskCreateView, TaskUpdateView

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
]
