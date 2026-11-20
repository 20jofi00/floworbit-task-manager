from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from tasks.models import Task, TaskType
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
