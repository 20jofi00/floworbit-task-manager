from django import forms
from django.views import generic
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from projects.models import Project
from tasks.forms import TaskSearchForm
from tasks.models import Task
from tasks.services import get_task_display_state
from teams.models import Team


class TasksListView(LoginRequiredMixin, generic.ListView):
    model = Task
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super(TasksListView, self).get_context_data(**kwargs)
        context["search_form"] = self.search_form
        context["team"] = self.team
        for task in context["task_list"]:
            task.state = get_task_display_state(task=task)
        return context

    def get_queryset(self):
        self.team = get_object_or_404(
            Team,
            pk=self.kwargs.get("team_pk"),
            members=self.request.user.id,
        )
        queryset = Task.objects.filter(project__team=self.team).order_by(
            "-deadline", "pk"
        )
        self.search_form = TaskSearchForm(self.request.GET)
        if self.search_form.is_valid():
            queryset = queryset.filter(
                name__icontains=self.search_form.cleaned_data["name"]
            )
        return queryset
