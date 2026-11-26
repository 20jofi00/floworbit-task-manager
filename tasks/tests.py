from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from tasks.models import Task, TaskAssignment, TaskDependency, TaskType, Tag
from tasks.services import (
    add_task_dependency,
    assign_worker_to_task,
    delete_task_dependency,
    get_task_display_state,
    propagate_task_completion,
    remove_worker_from_task,
    set_assignment_completion,
)
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

    def test_team_member_can_be_assigned(self):
        assignment = assign_worker_to_task(
            task=self.task,
            worker=self.worker,
        )

        self.assertEqual(assignment.task, self.task)
        self.assertEqual(assignment.worker, self.worker)
        self.assertFalse(assignment.is_completed)
        self.assertEqual(
            get_task_display_state(task=self.task),
            "in_progress",
        )

    def test_outsider_cannot_be_assigned(self):
        with self.assertRaises(ValidationError):
            assign_worker_to_task(
                task=self.task,
                worker=self.outsider,
            )

        self.assertFalse(TaskAssignment.objects.filter(task=self.task).exists())

    def test_duplicate_assignment_is_rejected(self):
        assign_worker_to_task(
            task=self.task,
            worker=self.worker,
        )

        with self.assertRaises(ValidationError):
            assign_worker_to_task(
                task=self.task,
                worker=self.worker,
            )

        self.assertEqual(
            TaskAssignment.objects.filter(
                task=self.task,
                worker=self.worker,
            ).count(),
            1,
        )

    def test_task_completion_requires_all_workers(self):
        assign_worker_to_task(self.task, self.worker)
        assign_worker_to_task(self.task, self.second_worker)

        set_assignment_completion(self.worker, self.task, True)

        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)

        set_assignment_completion(self.second_worker, self.task, True)

        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertEqual(
            get_task_display_state(task=self.task),
            "completed",
        )

        set_assignment_completion(self.worker, self.task, False)

        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)

    def test_removing_last_assignment_makes_task_unassigned(self):
        assign_worker_to_task(self.task, self.worker)
        set_assignment_completion(self.worker, self.task, True)

        remove_worker_from_task(
            task=self.task,
            worker=self.worker,
        )

        self.task.refresh_from_db()

        self.assertFalse(self.task.is_completed)
        self.assertFalse(TaskAssignment.objects.filter(task=self.task).exists())
        self.assertEqual(
            get_task_display_state(task=self.task),
            "unassigned",
        )

    def test_adding_worker_reopens_completed_task(self):
        assign_worker_to_task(self.task, self.worker)
        set_assignment_completion(self.worker, self.task, True)

        assign_worker_to_task(self.task, self.second_worker)

        self.task.refresh_from_db()

        self.assertFalse(self.task.is_completed)
        self.assertEqual(
            get_task_display_state(task=self.task),
            "in_progress",
        )

    def test_completion_changes_propagate_through_dependencies(self):
        assign_worker_to_task(self.prerequisite, self.worker)
        assign_worker_to_task(self.task, self.worker)
        assign_worker_to_task(self.third_task, self.worker)

        add_task_dependency(self.task, self.prerequisite)
        add_task_dependency(self.third_task, self.task)

        set_assignment_completion(self.worker, self.task, True)
        set_assignment_completion(self.worker, self.third_task, True)

        self.task.refresh_from_db()
        self.third_task.refresh_from_db()

        self.assertFalse(self.task.is_completed)
        self.assertFalse(self.third_task.is_completed)
        self.assertEqual(
            get_task_display_state(task=self.task),
            "blocked",
        )

        set_assignment_completion(self.worker, self.prerequisite, True)

        self.task.refresh_from_db()
        self.third_task.refresh_from_db()

        self.assertTrue(self.task.is_completed)
        self.assertTrue(self.third_task.is_completed)

        set_assignment_completion(self.worker, self.prerequisite, False)

        self.task.refresh_from_db()
        self.third_task.refresh_from_db()

        self.assertFalse(self.task.is_completed)
        self.assertFalse(self.third_task.is_completed)
        self.assertEqual(
            get_task_display_state(task=self.third_task),
            "blocked",
        )

    def test_dependency_cycle_is_rejected(self):
        add_task_dependency(self.task, self.prerequisite)
        add_task_dependency(self.prerequisite, self.third_task)

        with self.assertRaises(ValidationError):
            add_task_dependency(self.third_task, self.task)

        self.assertEqual(TaskDependency.objects.count(), 2)

    def test_task_cannot_depend_on_itself(self):
        with self.assertRaises(ValidationError):
            add_task_dependency(self.task, self.task)

        self.assertFalse(TaskDependency.objects.exists())

    def test_dependency_between_projects_is_rejected(self):
        another_project = Project.objects.create(
            name="Another project",
            team=self.team,
        )
        another_task = Task.objects.create(
            name="Another task",
            project=another_project,
            task_type=self.task_type,
            deadline=self.today,
        )

        with self.assertRaises(ValidationError):
            add_task_dependency(self.task, another_task)

        self.assertFalse(TaskDependency.objects.exists())

    def test_removing_dependency_recalculates_completion(self):
        assign_worker_to_task(self.task, self.worker)
        add_task_dependency(self.task, self.prerequisite)
        set_assignment_completion(self.worker, self.task, True)

        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)

        delete_task_dependency(
            dependent_task=self.task,
            prerequisite_task=self.prerequisite,
        )

        self.task.refresh_from_db()

        self.assertTrue(self.task.is_completed)
        self.assertFalse(TaskDependency.objects.exists())

    def test_task_can_move_to_project_in_same_team(self):
        another_project = Project.objects.create(
            name="Another project",
            team=self.team,
        )
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
                "name": self.task.name,
                "task_type": self.task_type.pk,
                "project": another_project.pk,
                "deadline": self.today.isoformat(),
                "priority": self.task.priority,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "projects:project-detail",
                kwargs={
                    "team_pk": self.team.pk,
                    "pk": another_project.pk,
                },
            ),
        )

        self.task.refresh_from_db()
        self.assertEqual(self.task.project_id, another_project.pk)

    def test_invalid_task_transfers_are_rejected(self):
        self.client.force_login(self.worker)

        url = reverse(
            "tasks:task-update",
            kwargs={
                "project_pk": self.project.pk,
                "pk": self.task.pk,
            },
        )
        data = {
            "name": self.task.name,
            "task_type": self.task_type.pk,
            "project": self.other_project.pk,
            "deadline": self.today.isoformat(),
            "priority": "high",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("project", response.context["form"].errors)

        self.task.refresh_from_db()
        self.assertEqual(self.task.project_id, self.project.pk)

        another_project = Project.objects.create(
            name="Another project",
            team=self.team,
        )
        add_task_dependency(self.task, self.prerequisite)

        data["project"] = another_project.pk
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("project", response.context["form"].errors)

        self.task.refresh_from_db()
        self.assertEqual(self.task.project_id, self.project.pk)

    def test_board_groups_tasks_by_state(self):
        assign_worker_to_task(self.task, self.worker)
        set_assignment_completion(self.worker, self.task, True)

        add_task_dependency(self.third_task, self.prerequisite)

        active_task = Task.objects.create(
            name="Active task",
            project=self.project,
            task_type=self.task_type,
            deadline=self.today,
        )
        assign_worker_to_task(active_task, self.worker)

        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "tasks:project-task-board",
                kwargs={"project_pk": self.project.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["unassigned_tasks"],
            [self.prerequisite],
        )
        self.assertEqual(
            response.context["tasks_in_progress"],
            [active_task],
        )
        self.assertEqual(
            response.context["blocked_tasks"],
            [self.third_task],
        )
        self.assertEqual(
            response.context["completed_tasks"],
            [self.task],
        )

    def test_calendar_groups_tasks_by_deadline(self):
        deadline = date(2026, 11, 18)

        self.task.deadline = deadline
        self.task.save()

        self.prerequisite.deadline = deadline
        self.prerequisite.save()

        self.third_task.deadline = date(2026, 12, 18)
        self.third_task.save()

        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "tasks:project-task-calendar",
                kwargs={"project_pk": self.project.pk},
            ),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["prev_month"],
            date(2026, 10, 1),
        )
        self.assertEqual(
            response.context["next_month"],
            date(2026, 12, 1),
        )

        calendar_tasks = []

        for week in response.context["calendar_weeks"]:
            for day in week:
                if day["date"] == deadline:
                    calendar_tasks.extend(day["tasks"])

        self.assertCountEqual(
            calendar_tasks,
            [self.task, self.prerequisite],
        )

    def test_calendar_rejects_invalid_month(self):
        self.client.force_login(self.worker)

        response = self.client.get(
            reverse(
                "tasks:project-task-calendar",
                kwargs={"project_pk": self.project.pk},
            ),
            {"year": 2026, "month": 13},
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_task_deletion_recalculates_dependent_task(self):
        self.worker.is_staff = True
        self.worker.is_superuser = True
        self.worker.save()
        self.client.force_login(self.worker)

        assign_worker_to_task(self.task, self.worker)
        add_task_dependency(self.task, self.prerequisite)
        set_assignment_completion(self.worker, self.task, True)

        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)

        response = self.client.post(
            reverse("admin:tasks_task_delete", args=[self.prerequisite.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.prerequisite.pk).exists())

        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)

    def test_admin_bulk_deletion_recalculates_remaining_task(self):
        self.worker.is_staff = True
        self.worker.is_superuser = True
        self.worker.save()
        self.client.force_login(self.worker)

        assign_worker_to_task(self.third_task, self.worker)
        add_task_dependency(self.task, self.prerequisite)
        add_task_dependency(self.third_task, self.task)
        set_assignment_completion(self.worker, self.third_task, True)

        self.third_task.refresh_from_db()
        self.assertFalse(self.third_task.is_completed)

        response = self.client.post(
            reverse("admin:tasks_task_changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [self.prerequisite.pk, self.task.pk],
                "post": "yes",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.prerequisite.pk).exists())
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

        self.third_task.refresh_from_db()
        self.assertTrue(self.third_task.is_completed)

    def test_task_pages_do_not_query_each_task(self):
        self.client.force_login(self.worker)

        tag = Tag.objects.create(name="backend")
        self.task.tags.add(tag)
        assign_worker_to_task(self.task, self.worker)
        add_task_dependency(self.task, self.prerequisite)

        urls = [
            reverse(
                "tasks:task-list",
                kwargs={"team_pk": self.team.pk},
            ),
            reverse(
                "tasks:project-task-board",
                kwargs={"project_pk": self.project.pk},
            ),
            reverse(
                "tasks:project-task-calendar",
                kwargs={"project_pk": self.project.pk},
            ),
        ]

        query_counts = []

        for url in urls:
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            query_counts.append(len(queries))

        for number in range(6):
            task = Task.objects.create(
                name=f"Extra task {number}",
                project=self.project,
                task_type=self.task_type,
                deadline=self.today,
            )
            task.tags.add(tag)
            assign_worker_to_task(task, self.worker)
            add_task_dependency(task, self.prerequisite)

        for url, query_count in zip(urls, query_counts):
            with self.subTest(url=url):
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    len(response.context["task_list"]),
                    9,
                )
                self.assertEqual(len(queries), query_count)

    def test_completion_handles_converging_dependency_paths(self):
        last_task = Task.objects.create(
            name="Last task",
            project=self.project,
            task_type=self.task_type,
            deadline=self.today,
        )

        for task in [
            self.prerequisite,
            self.task,
            self.third_task,
            last_task,
        ]:
            assign_worker_to_task(task, self.worker)

        add_task_dependency(last_task, self.prerequisite)
        add_task_dependency(self.task, self.prerequisite)
        add_task_dependency(self.third_task, self.task)
        add_task_dependency(last_task, self.third_task)

        for task in [self.task, self.third_task, last_task]:
            set_assignment_completion(self.worker, task, True)

        set_assignment_completion(
            self.worker,
            self.prerequisite,
            True,
        )

        for task in [
            self.prerequisite,
            self.task,
            self.third_task,
            last_task,
        ]:
            task.refresh_from_db()
            self.assertTrue(task.is_completed)

        set_assignment_completion(
            self.worker,
            self.prerequisite,
            False,
        )

        for task in [
            self.prerequisite,
            self.task,
            self.third_task,
            last_task,
        ]:
            task.refresh_from_db()
            self.assertFalse(task.is_completed)

    def test_propagation_rejects_stored_dependency_cycle(self):
        Task.objects.filter(pk=self.task.pk).update(
            is_completed=True,
        )

        TaskDependency.objects.bulk_create(
            [
                TaskDependency(
                    dependent_task=self.task,
                    prerequisite_task=self.prerequisite,
                ),
                TaskDependency(
                    dependent_task=self.prerequisite,
                    prerequisite_task=self.third_task,
                ),
                TaskDependency(
                    dependent_task=self.third_task,
                    prerequisite_task=self.task,
                ),
            ]
        )

        with self.assertRaises(ValidationError):
            propagate_task_completion(self.task)

        self.task.refresh_from_db()
        self.prerequisite.refresh_from_db()
        self.third_task.refresh_from_db()

        self.assertTrue(self.task.is_completed)
        self.assertFalse(self.prerequisite.is_completed)
        self.assertFalse(self.third_task.is_completed)
