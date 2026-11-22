from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from tasks.models import Task, TaskAssignment, TaskDependency, TaskType
from teams.forms import TeamAdminForm
from teams.models import Team
from teams.service import get_team_dashboard_stats
from teams.views import TeamWorkloadView


class TeamTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.worker = get_user_model().objects.create_user(
            username="test_worker",
            password="Blue!River73Cloud",
        )

        cls.second_worker = get_user_model().objects.create_user(
            username="second_worker",
            password="Blue!River73Cloud",
        )

        cls.team = Team.objects.create(name="Main team")
        cls.team.members.add(cls.worker, cls.second_worker)

        cls.other_team = Team.objects.create(name="Other team")

        cls.project = Project.objects.create(
            name="Main project",
            team=cls.team,
        )

        cls.task_type = TaskType.objects.create(name="Bug")

    def test_team_list_requires_login(self):
        url = reverse("teams:team-list")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={url}",
        )

    def test_team_list_shows_only_worker_teams(self):
        self.client.force_login(self.worker)

        response = self.client.get(reverse("teams:team-list"))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["team_list"],
            [self.team],
        )

    def test_team_pages_are_accessible_to_member(self):
        self.client.force_login(self.worker)

        names = [
            "teams:team-detail",
            "teams:team-dashboard",
            "teams:team-workload",
        ]

        for name in names:
            with self.subTest(name=name):
                response = self.client.get(reverse(name, kwargs={"pk": self.team.pk}))

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["team"], self.team)

    def test_foreign_team_pages_are_not_accessible(self):
        self.client.force_login(self.worker)

        names = [
            "teams:team-detail",
            "teams:team-dashboard",
            "teams:team-workload",
        ]

        for name in names:
            with self.subTest(name=name):
                response = self.client.get(
                    reverse(name, kwargs={"pk": self.other_team.pk})
                )

                self.assertEqual(response.status_code, 404)

    def test_team_search_filters_by_name(self):
        another_team = Team.objects.create(name="Design team")
        another_team.members.add(self.worker)

        self.client.force_login(self.worker)

        response = self.client.get(
            reverse("teams:team-list"),
            {"name": "MAIN"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["team_list"],
            [self.team],
        )

    def test_team_list_is_paginated(self):
        for number in range(5):
            team = Team.objects.create(name=f"Extra team {number}")
            team.members.add(self.worker)

        self.client.force_login(self.worker)

        first_response = self.client.get(reverse("teams:team-list"))
        second_response = self.client.get(
            reverse("teams:team-list"),
            {"page": 2},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.context["paginator"].count, 6)
        self.assertEqual(len(first_response.context["team_list"]), 5)
        self.assertEqual(len(second_response.context["team_list"]), 1)

    def test_empty_team_has_zero_dashboard_stats(self):
        result = get_team_dashboard_stats(team=self.team)

        self.assertEqual(
            result["stats"],
            {
                "total_tasks": 0,
                "completed_tasks": 0,
                "open_tasks": 0,
                "blocked_tasks": 0,
                "overdue_tasks": 0,
            },
        )

        project = result["projects"][0]

        self.assertEqual(project.total_tasks, 0)
        self.assertEqual(project.completed_tasks, 0)
        self.assertEqual(project.progress_percent, 0)

    def test_dashboard_counts_task_states_and_overdue_tasks(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        unassigned_task = Task.objects.create(
            name="Unassigned task",
            project=self.project,
            task_type=self.task_type,
            deadline=yesterday,
        )

        active_task = Task.objects.create(
            name="Active task",
            project=self.project,
            task_type=self.task_type,
            deadline=today,
        )
        TaskAssignment.objects.create(
            task=active_task,
            worker=self.worker,
        )

        Task.objects.create(
            name="Completed task",
            project=self.project,
            task_type=self.task_type,
            deadline=yesterday,
            is_completed=True,
        )

        blocked_task = Task.objects.create(
            name="Blocked task",
            project=self.project,
            task_type=self.task_type,
            deadline=yesterday,
        )
        TaskDependency.objects.create(
            dependent_task=blocked_task,
            prerequisite_task=unassigned_task,
        )

        other_project = Project.objects.create(
            name="Other project",
            team=self.other_team,
        )
        Task.objects.create(
            name="Foreign task",
            project=other_project,
            task_type=self.task_type,
            deadline=yesterday,
        )

        result = get_team_dashboard_stats(team=self.team)

        self.assertEqual(
            result["stats"],
            {
                "total_tasks": 4,
                "completed_tasks": 1,
                "open_tasks": 2,
                "blocked_tasks": 1,
                "overdue_tasks": 2,
            },
        )

        project = result["projects"][0]

        self.assertEqual(project.total_tasks, 4)
        self.assertEqual(project.completed_tasks, 1)
        self.assertEqual(project.progress_percent, 25)

    def test_workload_counts_only_team_assignments(self):
        today = timezone.localdate()

        incomplete_task = Task.objects.create(
            name="Incomplete task",
            project=self.project,
            task_type=self.task_type,
            deadline=today,
        )
        TaskAssignment.objects.create(
            task=incomplete_task,
            worker=self.worker,
        )

        completed_assignment_task = Task.objects.create(
            name="Task with completed personal work",
            project=self.project,
            task_type=self.task_type,
            deadline=today,
        )
        TaskAssignment.objects.create(
            task=completed_assignment_task,
            worker=self.worker,
            is_completed=True,
        )

        self.other_team.members.add(self.worker)

        other_project = Project.objects.create(
            name="Other project",
            team=self.other_team,
        )
        other_task = Task.objects.create(
            name="Other team task",
            project=other_project,
            task_type=self.task_type,
            deadline=today,
        )
        TaskAssignment.objects.create(
            task=other_task,
            worker=self.worker,
        )

        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "teams:team-workload",
                kwargs={"pk": self.team.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        members = {member.pk: member for member in response.context["members"]}

        self.assertEqual(
            members[self.worker.pk].incomplete_assignments,
            1,
        )
        self.assertEqual(
            members[self.worker.pk].completed_assignments,
            1,
        )
        self.assertEqual(
            members[self.second_worker.pk].incomplete_assignments,
            0,
        )
        self.assertEqual(
            members[self.second_worker.pk].completed_assignments,
            0,
        )

    def test_admin_form_allows_removing_unassigned_worker(self):
        form = TeamAdminForm(
            data={
                "name": self.team.name,
                "description": "",
                "members": [self.second_worker.pk],
            },
            instance=self.team,
        )

        self.assertTrue(form.is_valid())
        form.save()

        self.assertFalse(self.team.members.filter(pk=self.worker.pk).exists())
        self.assertTrue(self.team.members.filter(pk=self.second_worker.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.worker.pk).exists())

    def test_admin_form_rejects_removing_assigned_worker(self):
        task = Task.objects.create(
            name="Assigned task",
            project=self.project,
            task_type=self.task_type,
            deadline=timezone.localdate(),
        )
        TaskAssignment.objects.create(
            task=task,
            worker=self.worker,
        )

        form = TeamAdminForm(
            data={
                "name": self.team.name,
                "description": "",
                "members": [self.second_worker.pk],
            },
            instance=self.team,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("members", form.errors)
        self.assertTrue(self.team.members.filter(pk=self.worker.pk).exists())

    def test_dashboard_uses_fixed_queries(self):
        Task.objects.create(
            name="First task",
            project=self.project,
            task_type=self.task_type,
            deadline=timezone.localdate(),
        )

        with self.assertNumQueries(4):
            get_team_dashboard_stats(self.team)

        project = Project.objects.create(
            name="Another project",
            team=self.team,
        )

        for number in range(5):
            Task.objects.create(
                name=f"Extra task {number}",
                project=project,
                task_type=self.task_type,
                deadline=timezone.localdate(),
            )

        with self.assertNumQueries(4):
            data = get_team_dashboard_stats(self.team)

        self.assertEqual(data["stats"]["total_tasks"], 6)

    def test_workload_uses_one_member_query(self):
        view = TeamWorkloadView()
        view.object = self.team

        with self.assertNumQueries(1):
            context = view.get_context_data()
            list(context["members"])

        for number in range(5):
            worker = get_user_model().objects.create_user(
                username=f"extra_worker_{number}",
            )
            self.team.members.add(worker)

        with self.assertNumQueries(1):
            context = view.get_context_data()
            members = list(context["members"])

        self.assertEqual(len(members), 7)
