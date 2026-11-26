from django.contrib import admin

from teams.forms import TeamAdminForm
from teams.models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    form = TeamAdminForm
