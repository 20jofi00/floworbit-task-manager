from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from teams.models import Team


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
