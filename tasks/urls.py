from django.urls import path

from tasks.views import TasksListView

app_name = "tasks"

urlpatterns = [
    path("<int:team_pk>/", TasksListView.as_view(), name="tasks-list"),
]
