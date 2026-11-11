from django.views import generic
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from projects.forms import ProjectSearchForm
from projects.models import Project
from teams.models import Team


class ProjectListView(LoginRequiredMixin, generic.ListView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super(ProjectListView, self).get_context_data(**kwargs)
        context["search_form"] = self.search_form
        context["team"] = self.team
        return context

    def get_queryset(self):
        team = get_object_or_404(
            Team,
            pk=self.kwargs.get("team_pk"),
            members__id=self.request.user.id,
        )
        self.team = team
        queryset = Project.objects.filter(team=team)
        self.search_form = ProjectSearchForm(self.request.GET)
        if self.search_form.is_valid():
            queryset = queryset.filter(
                name__icontains=self.search_form.cleaned_data["name"]
            )
        return queryset


class ProjectDetailView(LoginRequiredMixin, generic.DetailView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        num_tasks = self.object.tasks.count()
        context["num_tasks"] = num_tasks
        if num_tasks == 0:
            context["num_completed_tasks"] = 0
            context["percent_of_completed_tasks"] = 0
            return context
        context["num_completed_tasks"] = self.object.tasks.filter(
            is_completed=True
        ).count()
        
        context["percent_of_completed_tasks"] = round(
            context["num_completed_tasks"] /
            context["num_tasks"] * 100,
            2
        )
        return context

    def get_queryset(self):
        team = get_object_or_404(
            Team,
            pk=self.kwargs.get("team_pk"),
            members__id=self.request.user.id,
        )
        return Project.objects.filter(team=team)
