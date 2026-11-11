from django.urls import path

from tasks.views import TaskListView, TaskDetailView

app_name = "tasks"

urlpatterns = [
    path("<int:team_pk>/", TaskListView.as_view(), name="task-list"),
    path("<int:team_pk>/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
