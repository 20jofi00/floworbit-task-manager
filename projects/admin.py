from django.contrib import admin

from projects.forms import ProjectAdminForm
from projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
