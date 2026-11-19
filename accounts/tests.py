from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class WorkerRegistrationTests(TestCase):
    def test_registration_creates_worker_and_logs_them_in(self):
        password = "PASSWORD_for_User"

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new_worker",
                "email": "worker@example.com",
                "first_name": "Alex",
                "last_name": "Smith",
                "password1": password,
                "password2": password,
            },
        )

        worker = get_user_model().objects.get(username="new_worker")

        self.assertEqual(worker.email, "worker@example.com")
        self.assertEqual(worker.first_name, "Alex")
        self.assertEqual(worker.last_name, "Smith")

        self.assertTrue(worker.check_password(password))
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(worker.pk),
        )
        self.assertRedirects(response, reverse("teams:team-list"))

    def test_registration_page_is_accessible(self):
        response = self.client.get(reverse("accounts:signup"))

        self.assertTemplateUsed(response, "registration/signup.html")
        self.assertEqual(response.status_code, 200)

    def test_registration_rejects_duplicate_username(self):
        password = "PASSWORD_for_User"

        username = "new_worker"

        get_user_model().objects.create_user(
            username=username,
            password=password,
        )
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": username,
                "password1": password,
                "password2": password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(
            get_user_model().objects.filter(username=username).count(),
            1,
        )

    def test_registration_rejects_mismatched_passwords(self):
        password = "PASSWORD_for_User"
        another_password = "another_PASSWORD_for_User"

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new_worker",
                "password1": password,
                "password2": another_password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(
            get_user_model().objects.filter(username="new_worker").exists()
        )

    def test_registration_rejects_weak_password(self):
        password = "1234678"

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new_worker",
                "password1": password,
                "password2": password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(
            get_user_model().objects.filter(username="new_worker").exists()
        )

    def test_registration_does_not_grant_admin_permissions(self):
        password = "PASSWORD_for_User"

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new_worker",
                "password1": password,
                "password2": password,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        worker = get_user_model().objects.get(username="new_worker")
        self.assertFalse(worker.is_staff)
        self.assertFalse(worker.is_superuser)

        self.assertRedirects(response, reverse("teams:team-list"))
