from django.urls import path

from teams.views import team_selection


app_name = "teams"

urlpatterns = [
    path("", team_selection, name="team_selection"),
]
