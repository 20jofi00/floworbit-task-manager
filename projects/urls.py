from django.urls import path

from projects.views import ProjectListView

app_name = "projects"

urlpatterns = [
    path("<int:team_pk>/", ProjectListView.as_view(), name="project-list"),
]
