from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from projects.models import Project
from tasks.dependencies import has_dependency_path
from tasks.models import Task, TaskAssignment, TaskDependency, TaskType
from tasks.services import add_task_dependency, assign_worker_to_task, set_assignment_completion
from teams.models import Team


class TaskReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.worker = get_user_model().objects.create_user(username="review_worker")
        cls.outsider = get_user_model().objects.create_user(username="review_outsider")
        cls.team = Team.objects.create(name="Review team")
        cls.team.members.add(cls.worker)
        cls.project = Project.objects.create(name="Review project", team=cls.team)
        cls.task_type = TaskType.objects.create(name="Review feature")
        cls.today = timezone.localdate()

    def make_task(self, name):
        return Task.objects.create(
            name=name,
            project=self.project,
            task_type=self.task_type,
            deadline=self.today,
        )

    def test_reachability_stops_when_existing_data_has_a_cycle(self):
        first = self.make_task("First")
        second = self.make_task("Second")
        unrelated = self.make_task("Unrelated")
        TaskDependency.objects.bulk_create([
            TaskDependency(dependent_task=first, prerequisite_task=second),
            TaskDependency(dependent_task=second, prerequisite_task=first),
        ])

        self.assertTrue(has_dependency_path(self.project.pk, first.pk, second.pk))
        self.assertFalse(has_dependency_path(self.project.pk, first.pk, unrelated.pk))


    def test_stored_cycle_rejects_completion_and_rolls_back_the_assignment(self):
        first = self.make_task("First")
        second = self.make_task("Second")
        assignment = assign_worker_to_task(first, self.worker)
        TaskDependency.objects.bulk_create([
            TaskDependency(dependent_task=first, prerequisite_task=second),
            TaskDependency(dependent_task=second, prerequisite_task=first),
        ])

        with self.assertRaisesMessage(ValidationError, "contain a cycle"):
            set_assignment_completion(self.worker, first, True)

        assignment.refresh_from_db()
        first.refresh_from_db()
        self.assertFalse(assignment.is_completed)
        self.assertFalse(first.is_completed)


    def test_admin_assignment_form_rejects_a_worker_outside_the_team(self):
        task = self.make_task("Task")
        self.worker.is_staff = True
        self.worker.is_superuser = True
        self.worker.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.worker)

        response = self.client.post(reverse("admin:tasks_taskassignment_add"), {
            "task": task.pk,
            "worker": self.outsider.pk,
            "_save": "Save",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("worker", response.context["adminform"].form.errors)
        self.assertFalse(TaskAssignment.objects.exists())


    def test_admin_dependency_form_rejects_a_cycle(self):
        first = self.make_task("First")
        second = self.make_task("Second")
        add_task_dependency(first, second)
        self.worker.is_staff = True
        self.worker.is_superuser = True
        self.worker.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.worker)

        response = self.client.post(reverse("admin:tasks_taskdependency_add"), {
            "dependent_task": second.pk,
            "prerequisite_task": first.pk,
            "_save": "Save",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("__all__", response.context["adminform"].form.errors)
        self.assertEqual(TaskDependency.objects.count(), 1)


    def test_personal_pagination_preserves_filters_and_completion_groups(self):
        for number in range(21):
            task = self.make_task(f"Review incomplete {number:02}")
            TaskAssignment.objects.create(task=task, worker=self.worker)

        for number in range(21):
            task = self.make_task(f"Review completed {number:02}")
            TaskAssignment.objects.create(
                task=task,
                worker=self.worker,
                is_completed=True,
            )

        unrelated_task = self.make_task("Unrelated task")
        TaskAssignment.objects.create(task=unrelated_task, worker=self.worker)

        self.client.force_login(self.worker)
        url = reverse("tasks:my-task-list")
        filters = {"name": "Review", "teams": self.team.pk}

        first = self.client.get(url, filters)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.context["incomplete_page"].paginator.count, 21)
        self.assertEqual(first.context["completed_page"].paginator.count, 21)
        self.assertEqual(len(first.context["incomplete_tasks"]), 20)
        self.assertEqual(len(first.context["completed_tasks"]), 20)

        second = self.client.get(url, {**filters, "incomplete_page": 2})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(second.context["incomplete_tasks"]), 1)
        self.assertEqual(len(second.context["completed_tasks"]), 20)
        self.assertEqual(second.context["completed_page"].number, 1)

        next_url = (
            f"?name=Review&teams={self.team.pk}"
            "&incomplete_page=2&completed_page=2"
        )
        self.assertContains(
            second,
            f'<a href="{next_url}" class="page-link">next</a>',
            html=True,
        )

        third = self.client.get(
            url,
            {**filters, "incomplete_page": 2, "completed_page": 2},
        )
        self.assertEqual(third.status_code, 200)
        self.assertEqual(len(third.context["incomplete_tasks"]), 1)
        self.assertEqual(len(third.context["completed_tasks"]), 1)
        self.assertFalse(third.context["incomplete_tasks"][0].my_assignment_completed)
        self.assertTrue(third.context["completed_tasks"][0].my_assignment_completed)


    def test_board_pagination_groups_only_current_page_tasks(self):
        Task.objects.bulk_create([
            Task(
                name=f"Board task {number:02}",
                project=self.project,
                task_type=self.task_type,
                deadline=self.today,
            )
            for number in range(43)
        ])
        self.client.force_login(self.worker)
        url = reverse("tasks:project-task-board", kwargs={"project_pk": self.project.pk})

        first = self.client.get(url)
        second = self.client.get(url, {"page": 2})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.context["paginator"].count, 43)
        self.assertEqual(len(first.context["unassigned_tasks"]), 40)
        self.assertEqual(len(second.context["unassigned_tasks"]), 3)
        self.assertContains(first, "Only tasks on this page appear below")
        first_ids = {task.pk for task in first.context["unassigned_tasks"]}
        second_ids = {task.pk for task in second.context["unassigned_tasks"]}
        self.assertFalse(first_ids & second_ids)


    def test_calendar_pagination_keeps_month_parameters_and_all_tasks(self):
        Task.objects.bulk_create([
            Task(
                name=f"Calendar task {number:03}",
                project=self.project,
                task_type=self.task_type,
                deadline=self.today,
            )
            for number in range(103)
        ])
        next_month = (self.today.replace(day=1) + timedelta(days=32)).replace(day=1)
        Task.objects.create(
            name="Next month task",
            project=self.project,
            task_type=self.task_type,
            deadline=next_month,
        )
        self.client.force_login(self.worker)
        url = reverse("tasks:project-task-calendar", kwargs={"project_pk": self.project.pk})
        filters = {"year": self.today.year, "month": self.today.month}

        first = self.client.get(url, filters)
        second = self.client.get(url, {**filters, "page": 2})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.context["paginator"].count, 103)
        self.assertContains(first, f'year={self.today.year}&amp;month={self.today.month}&amp;page=2')
        pages = []
        for response in [first, second]:
            ids = {
                task.pk
                for week in response.context["calendar_weeks"]
                for day in week
                for task in day["tasks"]
            }
            self.assertEqual(ids, {task.pk for task in response.context["task_list"]})
            pages.append(ids)
        self.assertEqual(len(pages[0]), 100)
        self.assertEqual(len(pages[1]), 3)
        self.assertFalse(pages[0] & pages[1])


    def test_personal_task_queries_do_not_grow_per_assignment(self):
        root = self.make_task("Prerequisite")
        first = self.make_task("First")
        assign_worker_to_task(first, self.worker)
        add_task_dependency(first, root)
        self.client.force_login(self.worker)
        url = reverse("tasks:my-task-list")

        with CaptureQueriesContext(connection) as small:
            first_response = self.client.get(url)

        for number in range(6):
            task = self.make_task(f"Extra task {number}")
            assign_worker_to_task(task, self.worker)
            add_task_dependency(task, root)

        with CaptureQueriesContext(connection) as large:
            second_response = self.client.get(url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(second_response.context["task_list"]), 7)
        self.assertEqual(len(small), len(large))

