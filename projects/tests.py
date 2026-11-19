from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from projects.models import Project
from tasks.models import Task, TaskType
from teams.models import Team


class ProjectViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.worker = get_user_model().objects.create_user(
            username="test_worker",
            password="Blue!River73Cloud",
        )

        cls.team = Team.objects.create(name="Main team")
        cls.team.members.add(cls.worker)

        cls.other_team = Team.objects.create(name="Other team")

        cls.project = Project.objects.create(
            name="Main project",
            description="Project description",
            team=cls.team,
        )

        cls.other_project = Project.objects.create(
            name="Other project",
            team=cls.other_team,
        )

    def test_foreign_team_project_posts_are_rejected(self):
        self.client.force_login(self.worker)

        response = self.client.post(
            reverse(
                "projects:project-create",
                kwargs={"team_pk": self.other_team.pk},
            ),
            {
                "name": "New project",
            },
        )
        response_update = self.client.post(
            reverse(
                "projects:project-update",
                kwargs={
                    "team_pk": self.other_team.pk,
                    "pk": self.other_project.pk,
                },
            ),
            {
                "name": "New project",
                "description": "new project description",
            },
        )

        self.other_project.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_update.status_code, 404)
        self.assertFalse(Project.objects.filter(name="New project").exists())
        self.assertEqual(self.other_project.team.pk, self.other_team.pk)
        self.assertEqual(self.other_project.name, "Other project")
        self.assertEqual(self.other_project.description, "")

    def test_project_pagination_preserves_search(self):
        Project.objects.create(
            name="First project",
            team=self.team,
        )
        Project.objects.create(
            name="Second project",
            team=self.team,
        )
        Project.objects.create(
            name="Third project",
            team=self.team,
        )
        Project.objects.create(
            name="Fourth project",
            team=self.team,
        )
        Project.objects.create(
            name="Fifth project",
            team=self.team,
        )
        Project.objects.create(
            name="Six",
            team=self.team,
        )

        self.client.force_login(self.worker)
        response = self.client.get(
            reverse("projects:project-list", kwargs={"team_pk": self.team.pk}),
            {"name": "Project"},
        )

        self.assertEqual(Project.objects.all().count(), 8)
        self.assertEqual(response.context["paginator"].count, 6)
        self.assertEqual(len(response.context["project_list"]), 5)

        next_url = "?name=Project&page=2"

        self.assertContains(
            response,
            f'<a href="{next_url}" class="page-link">next</a>',
            html=True,
        )

        response2 = self.client.get(
            reverse("projects:project-list", kwargs={"team_pk": self.team.pk})
            + next_url,
        )

        self.assertEqual(response2.status_code, 200)
        self.assertEqual(len(response2.context["project_list"]), 1)
        self.assertEqual(response2.context["project_list"][0].name, "Third project")

    def test_project_progress_counts_completed_tasks(self):
        task_type = TaskType.objects.create(name="test")
        Task.objects.create(
            name="completed_task",
            task_type=task_type,
            project=self.project,
            deadline="2026-11-18",
            priority="low",
            is_completed=True,
        )

        Task.objects.create(
            name="first_uncompleted_task",
            task_type=task_type,
            project=self.project,
            deadline="2026-11-18",
            priority="medium",
        )
        Task.objects.create(
            name="second_uncompleted_task",
            task_type=task_type,
            project=self.project,
            deadline="2026-11-18",
            priority="low",
        )

        self.client.force_login(self.worker)
        response = self.client.get(
            reverse(
                "projects:project-detail",
                kwargs={
                    "team_pk": self.team.pk,
                    "pk": self.project.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["num_tasks"], 3)
        self.assertEqual(response.context["num_completed_tasks"], 1)
        self.assertEqual(response.context["percent_of_completed_tasks"], 33.33)
