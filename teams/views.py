from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q

from teams.forms import TeamSearchForm
from teams.models import Team
from teams.service import get_team_dashboard_stats


class TeamListView(LoginRequiredMixin, generic.ListView):
    model = Team
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(TeamListView, self).get_context_data(**kwargs)
        context["search_form"] = self.search_form
        return context

    def get_queryset(self):
        queryset = Team.objects.filter(members__id=self.request.user.id).order_by("pk")
        self.search_form = TeamSearchForm(self.request.GET)
        if self.search_form.is_valid():
            queryset = queryset.filter(
                name__icontains=self.search_form.cleaned_data["name"]
            )
        return queryset


class TeamDetailView(LoginRequiredMixin, generic.DetailView):
    model = Team

    def get_queryset(self):
        queryset = Team.objects.filter(
            members__id=self.request.user.id
        ).prefetch_related("members__position")
        return queryset


class TeamDashboardView(LoginRequiredMixin, generic.DetailView):
    model = Team
    template_name = "teams/team_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super(TeamDashboardView, self).get_context_data(**kwargs)
        context["team"] = self.object
        stats = get_team_dashboard_stats(team=self.object)
        context["stats"] = stats["stats"]
        context["projects"] = stats["projects"]
        return context

    def get_queryset(self):
        queryset = Team.objects.filter(members__id=self.request.user.id).order_by("pk")
        return queryset


class TeamWorkloadView(LoginRequiredMixin, generic.DetailView):
    model = Team
    template_name = "teams/team_workload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team"] = self.object

        context["members"] = (
            self.object.members.select_related("position")
            .annotate(
                incomplete_assignments=Count(
                    "task_assignments",
                    filter=Q(
                        task_assignments__task__project__team=self.object,
                        task_assignments__is_completed=False,
                    ),
                    distinct=True,
                ),
                completed_assignments=Count(
                    "task_assignments",
                    filter=Q(
                        task_assignments__task__project__team=self.object,
                        task_assignments__is_completed=True,
                    ),
                    distinct=True,
                ),
            )
            .order_by("pk")
        )

        return context

    def get_queryset(self):
        queryset = Team.objects.filter(members__id=self.request.user.id).order_by("pk")
        return queryset
