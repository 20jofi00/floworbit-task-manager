from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("teams.urls", namespace="teams")),
    path("projects/", include("projects.urls", namespace="projects")),
    path("tasks/", include("tasks.urls", namespace="tasks")),
    path("accounts/", include("django.contrib.auth.urls")),
]
