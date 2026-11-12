from django.urls import reverse
from django.views import generic
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from projects.models import Project
from tasks.forms import TaskForm, TaskSearchForm
from tasks.models import Task, TaskAssignment, TaskDependency
from tasks.services import get_task_display_state
from teams.models import Team


class TaskListView(LoginRequiredMixin, generic.ListView):
    model = Task
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
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


class TaskDetailView(LoginRequiredMixin, generic.DetailView):
    model = Task

    def get_context_data(self, **kwargs):
        context = super(TaskDetailView, self).get_context_data(**kwargs)
        prerequisite_ids = TaskDependency.objects.filter(
            dependent_task=self.object
        ).values_list("prerequisite_task", flat=True)
        context["prerequisite_tasks"] = Task.objects.filter(id__in=prerequisite_ids)
        context["task"] = self.object
        self.object.state = get_task_display_state(task=self.object)
        context["assignments"] = TaskAssignment.objects.filter(task=self.object)
        return context

    def get_queryset(self):
        self.team = get_object_or_404(
            Team,
            pk=self.kwargs.get("team_pk"),
            members=self.request.user.id,
        )
        return Task.objects.filter(project__team=self.team).order_by("-deadline", "pk")


class TaskCreateView(LoginRequiredMixin, generic.CreateView):
    model = Task
    form_class = TaskForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.project = get_object_or_404(
            Project,
            pk=self.kwargs.get("project_pk"),
            team__members=self.request.user.id,
        )
        kwargs["team"] = self.project.team
        return kwargs

    def get_success_url(self):
        return reverse(
            "projects:project-detail",
            kwargs={"team_pk": self.project.team.id, "pk": self.project.id},
        )

    def form_valid(self, form):
        form.instance.project = self.project
        return super().form_valid(form)
