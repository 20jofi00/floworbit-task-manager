from django.urls import path

from projects.views import ProjectListView, ProjectDetailView


app_name = "projects"

urlpatterns = [
    path("<int:team_pk>/", ProjectListView.as_view(), name="project-list"),
    path("<int:team_pk>/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
]
