from django.urls import path

from teams.views import (
    TeamListView,
)

app_name = "teams"

urlpatterns = [
    path("", TeamListView.as_view(), name="team-list"),
]
