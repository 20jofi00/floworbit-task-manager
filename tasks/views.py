from django.urls import reverse
from django.shortcuts import render
from django.views import generic
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError

from projects.models import Project
from tasks.forms import TaskForm, TaskUpdateForm, TaskSearchForm, AssignWorkerForm
from tasks.models import Task, TaskAssignment, TaskDependency
from tasks.services import (
    assign_worker_to_task,
    get_task_display_state,
)
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
        context["form"] = AssignWorkerForm(team=self.object.project.team)
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
        return kwargs

    def get_success_url(self):
        return reverse(
            "projects:project-detail",
            kwargs={"team_pk": self.project.team.id, "pk": self.project.id},
        )

    def form_valid(self, form):
        form.instance.project = self.project
        return super().form_valid(form)


class TaskUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Task
    form_class = TaskUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.project
        return kwargs

    def get_success_url(self):
        return reverse(
            "projects:project-detail",
            kwargs={
                "team_pk": self.object.project.team.id,
                "pk": self.object.project.id,
            },
        )

    def get_queryset(self):
        self.project = get_object_or_404(
            Project,
            pk=self.kwargs.get("project_pk"),
            team__members=self.request.user.id,
        )
        queryset = Task.objects.filter(project=self.project)
        return queryset


class AssignWorkerView(LoginRequiredMixin, generic.FormView):
    form_class = AssignWorkerForm
    http_method_names = ["post"]

    def post(self, request, project_pk: int, pk: int):
        project = get_object_or_404(
            Project,
            pk=project_pk,
            team__members=self.request.user.id,
        )
        task = get_object_or_404(
            Task,
            pk=pk,
            project=project,
        )

        form = AssignWorkerForm(request.POST, team=task.project.team)
        if form.is_valid():
            worker = form.cleaned_data["worker"]
            try:
                assign_worker_to_task(task=task, worker=worker)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return redirect(
                    reverse(
                        "tasks:task-participants",
                        kwargs={
                            "team_pk": project.team.id,
                            "pk": task.id,
                        },
                    )
                )
        context = {
            "task": task,
            "form": form,
            "assignments": TaskAssignment.objects.filter(task=task),
        }
        return render(request, "tasks/task_participants.html", context)
