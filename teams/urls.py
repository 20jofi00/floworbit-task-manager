from django.urls import path

from teams.views import (
    TeamDashboardView,
    TeamListView,
    TeamDetailView,
)

app_name = "teams"

urlpatterns = [
    path("", TeamListView.as_view(), name="team-list"),
    path("team/<int:pk>/", TeamDetailView.as_view(), name="team-detail"),
    path(
        "team/<int:pk>/dashboard/", TeamDashboardView.as_view(), name="team-dashboard"
    ),
]
