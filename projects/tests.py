from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from projects.forms import ProjectAdminForm
from projects.models import Project
from projects.service import move_project_to_team
from tasks.models import Task, TaskType
from teams.models import Team


class ProjectTests(TestCase):
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

        cls.task_type = TaskType.objects.create(name="Bug")

    def test_project_list_requires_login(self):
        url = reverse(
            "projects:project-list",
            kwargs={"team_pk": self.team.pk},
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={url}",
        )

    def test_project_list_shows_only_selected_team_projects(self):
        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "projects:project-list",
                kwargs={"team_pk": self.team.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["project_list"],
            [self.project],
        )

    def test_project_create_saves_project(self):
        self.client.force_login(self.worker)

        response = self.client.post(
            reverse(
                "projects:project-create",
                kwargs={"team_pk": self.team.pk},
            ),
            {
                "name": "New project",
                "description": "New description",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "projects:project-list",
                kwargs={"team_pk": self.team.pk},
            ),
        )

        project = Project.objects.get(name="New project")

        self.assertEqual(project.team, self.team)
        self.assertEqual(project.description, "New description")

    def test_project_update_saves_changes(self):
        self.client.force_login(self.worker)

        response = self.client.post(
            reverse(
                "projects:project-update",
                kwargs={
                    "team_pk": self.team.pk,
                    "pk": self.project.pk,
                },
            ),
            {
                "name": "Updated project",
                "description": "Updated description",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "projects:project-detail",
                kwargs={
                    "team_pk": self.team.pk,
                    "pk": self.project.pk,
                },
            ),
        )

        self.project.refresh_from_db()

        self.assertEqual(self.project.name, "Updated project")
        self.assertEqual(self.project.description, "Updated description")
        self.assertEqual(self.project.team, self.team)

    def test_project_rejects_duplicate_name(self):
        self.client.force_login(self.worker)

        response = self.client.post(
            reverse(
                "projects:project-create",
                kwargs={"team_pk": self.team.pk},
            ),
            {"name": self.project.name},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertEqual(
            Project.objects.filter(
                name=self.project.name,
                team=self.team,
            ).count(),
            1,
        )

    def test_foreign_team_project_posts_are_rejected(self):
        self.client.force_login(self.worker)

        create_response = self.client.post(
            reverse(
                "projects:project-create",
                kwargs={"team_pk": self.other_team.pk},
            ),
            {"name": "New project"},
        )

        update_response = self.client.post(
            reverse(
                "projects:project-update",
                kwargs={
                    "team_pk": self.other_team.pk,
                    "pk": self.other_project.pk,
                },
            ),
            {
                "name": "New project",
                "description": "New description",
            },
        )

        self.assertEqual(create_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertFalse(Project.objects.filter(name="New project").exists())

        self.other_project.refresh_from_db()

        self.assertEqual(self.other_project.name, "Other project")
        self.assertEqual(self.other_project.description, "")
        self.assertEqual(self.other_project.team, self.other_team)

    def test_project_pagination_preserves_search(self):
        names = [
            "First project",
            "Second project",
            "Third project",
            "Fourth project",
            "Fifth project",
            "Six",
        ]

        for name in names:
            Project.objects.create(name=name, team=self.team)

        self.client.force_login(self.worker)

        url = reverse(
            "projects:project-list",
            kwargs={"team_pk": self.team.pk},
        )

        response = self.client.get(url, {"name": "Project"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 6)
        self.assertEqual(len(response.context["project_list"]), 5)

        next_url = "?name=Project&page=2"

        self.assertContains(
            response,
            f'<a href="{next_url}" class="page-link">next</a>',
            html=True,
        )

        next_response = self.client.get(url + next_url)

        self.assertEqual(next_response.status_code, 200)
        self.assertEqual(
            len(next_response.context["project_list"]),
            1,
        )
        self.assertEqual(
            next_response.context["project_list"][0].name,
            "Third project",
        )

    def test_project_progress_counts_completed_tasks(self):
        Task.objects.create(
            name="Completed task",
            task_type=self.task_type,
            project=self.project,
            deadline="2026-11-18",
            is_completed=True,
        )

        Task.objects.create(
            name="First incomplete task",
            task_type=self.task_type,
            project=self.project,
            deadline="2026-11-18",
        )

        Task.objects.create(
            name="Second incomplete task",
            task_type=self.task_type,
            project=self.project,
            deadline="2026-11-18",
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
        self.assertEqual(
            response.context["percent_of_completed_tasks"],
            33.33,
        )

    def test_empty_project_has_zero_progress(self):
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
        self.assertEqual(response.context["num_tasks"], 0)
        self.assertEqual(response.context["num_completed_tasks"], 0)
        self.assertEqual(
            response.context["percent_of_completed_tasks"],
            0,
        )

    def test_empty_project_can_be_moved(self):
        move_project_to_team(
            team=self.other_team,
            project=self.project,
        )

        self.project.refresh_from_db()

        self.assertEqual(self.project.team, self.other_team)

    def test_project_with_tasks_cannot_be_moved(self):
        Task.objects.create(
            name="Existing task",
            task_type=self.task_type,
            project=self.project,
            deadline="2026-11-18",
        )

        with self.assertRaises(ValidationError):
            move_project_to_team(
                team=self.other_team,
                project=self.project,
            )

        self.project.refresh_from_db()

        self.assertEqual(self.project.team, self.team)

    def test_admin_form_rejects_moving_project_with_tasks(self):
        Task.objects.create(
            name="Existing task",
            task_type=self.task_type,
            project=self.project,
            deadline="2026-11-18",
        )

        form = ProjectAdminForm(
            data={
                "name": self.project.name,
                "description": self.project.description,
                "team": self.other_team.pk,
            },
            instance=self.project,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("team", form.errors)

        self.project.refresh_from_db()

        self.assertEqual(self.project.team, self.team)
