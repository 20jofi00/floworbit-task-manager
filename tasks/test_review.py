from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from projects.models import Project
from tasks.dependencies import has_dependency_path
from tasks.models import Task, TaskDependency, TaskType
from tasks.services import assign_worker_to_task, set_assignment_completion
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

