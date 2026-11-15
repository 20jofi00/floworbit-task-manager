from django.urls import reverse
from django.shortcuts import render
from django.views import generic
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError

from projects.models import Project
from tasks.forms import (
    TaskForm,
    TaskUpdateForm,
    TaskSearchForm,
    AssignWorkerForm,
    TaskAddDependencyForm,
    TeamTaskForm,
)
from tasks.models import Task, TaskAssignment, TaskDependency
from tasks.services import (
    add_task_dependency,
    assign_worker_to_task,
    delete_task_dependency,
    get_task_display_state,
    remove_worker_from_task,
    set_assignment_completion,
)
from teams.models import Team


def get_accessible_task(project_pk: int, task_pk: int, user_id: int) -> Task:
    project = get_object_or_404(
        Project,
        pk=project_pk,
        team__members=user_id,
    )
    return get_object_or_404(
        Task,
        pk=task_pk,
        project=project,
    )


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

        context["dependency_form"] = TaskAddDependencyForm(
            project=self.object.project, task=self.object
        )

        context["my_assignment"] = TaskAssignment.objects.filter(
            task=self.object,
            worker=self.request.user,
        ).first()

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
        task = get_accessible_task(
            project_pk=project_pk, task_pk=pk, user_id=self.request.user.id
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
                            "team_pk": task.project.team.id,
                            "pk": task.id,
                        },
                    )
                )
        context = {
            "task": task,
            "form": form,
            "assignments": TaskAssignment.objects.filter(task=task),
            "my_assignment": TaskAssignment.objects.filter(
                task=task,
                worker=self.request.user,
            ).first(),
        }
        return render(request, "tasks/task_participants.html", context)


class RemoveWorkerView(LoginRequiredMixin, generic.FormView):
    http_method_names = ["post"]

    def post(self, request, project_pk: int, pk: int, worker_pk: int):
        task = get_accessible_task(
            project_pk=project_pk, task_pk=pk, user_id=self.request.user.id
        )

        assignment = get_object_or_404(
            TaskAssignment,
            task=task,
            worker_id=worker_pk,
        )
        remove_worker_from_task(task=task, worker=assignment.worker)
        return redirect(
            reverse(
                "tasks:task-participants",
                kwargs={
                    "team_pk": task.project.team.id,
                    "pk": task.id,
                },
            )
        )


class AssignmentWorkerView(LoginRequiredMixin, generic.FormView):
    http_method_names = ["post"]

    def post(self, request, project_pk: int, pk: int):
        task = get_accessible_task(
            project_pk=project_pk, task_pk=pk, user_id=self.request.user.id
        )
        assignment = get_object_or_404(
            TaskAssignment,
            task=task,
            worker=request.user,
        )
        set_assignment_completion(
            task=task,
            worker=request.user,
            is_completed=not assignment.is_completed,
        )
        return redirect(
            reverse(
                "tasks:task-participants",
                kwargs={
                    "team_pk": task.project.team.id,
                    "pk": task.id,
                },
            )
        )


class TaskAddDependencyView(LoginRequiredMixin, generic.FormView):
    form_class = TaskAddDependencyForm
    http_method_names = ["post"]

    def post(self, request, project_pk: int, pk: int):
        task = get_accessible_task(
            project_pk=project_pk, task_pk=pk, user_id=self.request.user.id
        )

        dependency_form = TaskAddDependencyForm(
            request.POST, project=task.project, task=task
        )
        if dependency_form.is_valid():
            prerequisite_task = dependency_form.cleaned_data["prerequisite_task"]
            try:
                add_task_dependency(
                    dependent_task=task,
                    prerequisite_task=prerequisite_task,
                )
            except ValidationError as error:
                dependency_form.add_error(None, error)
            else:
                return redirect(
                    reverse(
                        "tasks:task-detail",
                        kwargs={
                            "team_pk": task.project.team.id,
                            "pk": task.id,
                        },
                    )
                )
        tasks_dependency_ids = TaskDependency.objects.filter(
            dependent_task=task
        ).values_list("prerequisite_task", flat=True)
        tasks_dependency = Task.objects.filter(id__in=tasks_dependency_ids)
        task.state = get_task_display_state(task=task)
        context = {
            "task": task,
            "dependency_form": dependency_form,
            "prerequisite_tasks": tasks_dependency,
        }
        return render(request, "tasks/task_detail.html", context)


class TaskRemoveDependencyView(LoginRequiredMixin, generic.FormView):
    http_method_names = ["post"]

    def post(
        self,
        request,
        project_pk: int,
        pk: int,
        prerequisite_task_pk: int,
    ):
        task = get_accessible_task(
            project_pk=project_pk, task_pk=pk, user_id=self.request.user.id
        )
        prerequisite_task = get_object_or_404(
            Task,
            pk=prerequisite_task_pk,
            project=task.project,
        )
        get_object_or_404(
            TaskDependency,
            dependent_task=task,
            prerequisite_task=prerequisite_task,
        )

        delete_task_dependency(dependent_task=task, prerequisite_task=prerequisite_task)

        return redirect(
            reverse(
                "tasks:task-detail",
                kwargs={
                    "team_pk": task.project.team.id,
                    "pk": task.id,
                },
            )
        )


class MyTaskListView(LoginRequiredMixin, generic.ListView):
    model = Task
    template_name = "tasks/my_task_list.html"

    def get_context_data(self, **kwargs):
        context = super(MyTaskListView, self).get_context_data(**kwargs)
        context["search_form"] = self.search_form
        context["completed_tasks"] = []
        context["incomplete_tasks"] = []

        task_assignments = {}

        for task_assignment in self.task_assignments:
            task_assignments[task_assignment.task_id] = task_assignment

        for task in self.object_list:
            task.state = get_task_display_state(task=task)
            if task_assignments[task.id].is_completed:
                context["completed_tasks"].append(task)
            else:
                context["incomplete_tasks"].append(task)
        return context

    def get_queryset(self):
        self.task_assignments = TaskAssignment.objects.filter(worker=self.request.user)

        self.queryset = Task.objects.filter(
            id__in=self.task_assignments.values_list(
                "task",
                flat=True,
            )
        ).order_by("-deadline", "pk")

        self.search_form = TeamTaskForm(self.request.GET, user=self.request.user)
        if self.search_form.is_valid():
            if self.search_form.cleaned_data["teams"]:
                self.queryset = self.queryset.filter(
                    project__team__in=self.search_form.cleaned_data["teams"]
                )
            if self.search_form.cleaned_data["name"]:
                self.queryset = self.queryset.filter(
                    name__icontains=self.search_form.cleaned_data["name"]
                )
        return self.queryset
