from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from tasks.models import Task, TaskAssignment, TaskType
from teams.models import Team


class TaskTests(TestCase):
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
        cls.outsider = get_user_model().objects.create_user(
            username="outsider",
            password="Blue!River73Cloud",
        )

        cls.team = Team.objects.create(name="Main team")
        cls.team.members.add(cls.worker, cls.second_worker)

        cls.other_team = Team.objects.create(name="Other team")
        cls.other_team.members.add(cls.outsider)

        cls.project = Project.objects.create(
            name="Main project",
            team=cls.team,
        )
        cls.other_project = Project.objects.create(
            name="Other project",
            team=cls.other_team,
        )

        cls.task_type = TaskType.objects.create(name="Bug")
        cls.today = timezone.localdate()

        cls.task = Task.objects.create(
            name="Main task",
            project=cls.project,
            task_type=cls.task_type,
            deadline=cls.today,
            priority="high",
        )
        cls.prerequisite = Task.objects.create(
            name="Prerequisite",
            project=cls.project,
            task_type=cls.task_type,
            deadline=cls.today,
            priority="low",
        )
        cls.third_task = Task.objects.create(
            name="Third task",
            project=cls.project,
            task_type=cls.task_type,
            deadline=cls.today,
        )
        cls.foreign_task = Task.objects.create(
            name="Foreign task",
            project=cls.other_project,
            task_type=cls.task_type,
            deadline=cls.today,
        )

    def test_task_list_requires_login(self):
        url = reverse(
            "tasks:task-list",
            kwargs={"team_pk": self.team.pk},
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={url}",
        )

    def test_task_list_shows_only_selected_team_tasks(self):
        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "tasks:task-list",
                kwargs={"team_pk": self.team.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["task_list"],
            [self.task, self.prerequisite, self.third_task],
        )

    def test_outsider_cannot_view_or_change_tasks(self):
        self.client.force_login(self.outsider)

        detail_response = self.client.get(
            reverse(
                "tasks:task-detail",
                kwargs={"team_pk": self.team.pk, "pk": self.task.pk},
            )
        )

        create_response = self.client.post(
            reverse(
                "tasks:task-create",
                kwargs={"project_pk": self.project.pk},
            ),
            {
                "name": "Unauthorized task",
                "task_type": self.task_type.pk,
                "deadline": self.today.isoformat(),
                "priority": "high",
            },
        )

        update_response = self.client.post(
            reverse(
                "tasks:task-update",
                kwargs={
                    "project_pk": self.project.pk,
                    "pk": self.task.pk,
                },
            ),
            {
                "name": "Unauthorized change",
                "task_type": self.task_type.pk,
                "project": self.project.pk,
                "deadline": self.today.isoformat(),
                "priority": "high",
            },
        )

        assignment_response = self.client.post(
            reverse(
                "tasks:task-add-worker",
                kwargs={
                    "project_pk": self.project.pk,
                    "pk": self.task.pk,
                },
            ),
            {"worker": self.outsider.pk},
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(create_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(assignment_response.status_code, 404)

        self.task.refresh_from_db()

        self.assertEqual(self.task.name, "Main task")
        self.assertFalse(Task.objects.filter(name="Unauthorized task").exists())
        self.assertFalse(TaskAssignment.objects.filter(task=self.task).exists())

    def test_task_create_saves_task(self):
        self.client.force_login(self.worker)

        response = self.client.post(
            reverse(
                "tasks:task-create",
                kwargs={"project_pk": self.project.pk},
            ),
            {
                "name": "New task",
                "description": "Task description",
                "task_type": self.task_type.pk,
                "deadline": self.today.isoformat(),
                "priority": "high",
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

        task = Task.objects.get(name="New task")

        self.assertEqual(task.project, self.project)
        self.assertEqual(task.description, "Task description")
        self.assertEqual(task.priority, "high")
        self.assertFalse(task.is_completed)

    def test_task_update_saves_changes(self):
        self.client.force_login(self.worker)

        response = self.client.post(
            reverse(
                "tasks:task-update",
                kwargs={
                    "project_pk": self.project.pk,
                    "pk": self.task.pk,
                },
            ),
            {
                "name": "Updated task",
                "description": "Updated description",
                "task_type": self.task_type.pk,
                "project": self.project.pk,
                "deadline": self.today.isoformat(),
                "priority": "low",
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

        self.task.refresh_from_db()

        self.assertEqual(self.task.name, "Updated task")
        self.assertEqual(self.task.description, "Updated description")
        self.assertEqual(self.task.priority, "low")

    def test_task_search_and_priority_filter(self):
        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "tasks:task-list",
                kwargs={"team_pk": self.team.pk},
            ),
            {
                "name": "task",
                "priority": "high",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["task_list"],
            [self.task],
        )

    def test_my_tasks_are_grouped_by_personal_completion(self):
        TaskAssignment.objects.create(
            task=self.task,
            worker=self.worker,
            is_completed=True,
        )
        TaskAssignment.objects.create(
            task=self.prerequisite,
            worker=self.worker,
        )
        TaskAssignment.objects.create(
            task=self.third_task,
            worker=self.second_worker,
        )

        self.client.force_login(self.worker)

        response = self.client.get(reverse("tasks:my-task-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["completed_tasks"],
            [self.task],
        )
        self.assertEqual(
            response.context["incomplete_tasks"],
            [self.prerequisite],
        )
