from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def team_selection(request: HttpRequest) -> HttpResponse:
    return render(request, "teams/team_selection.html")
