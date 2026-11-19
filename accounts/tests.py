from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class WorkerRegistrationTests(TestCase):
    def test_registration_creates_worker_and_logs_them_in(self):
        password = "Blue!River73Cloud"

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
        password = "Blue!River73Cloud"

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
        password = "Blue!River73Cloud"
        another_password = "another_Blue!River73Cloud"

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
        password = "Blue!River73Cloud"

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


class WorkerAuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "Blue!River73Cloud"
        cls.worker = get_user_model().objects.create_user(
            username="test_worker",
            password=cls.password,
        )

    def test_login_page_is_accessible(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.worker.username,
                "password": self.password,
            },
        )

        self.assertRedirects(response, reverse("teams:team-list"))
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.worker.pk),
        )

    def test_login_rejects_invalid_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.worker.username,
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rejects_unknown_username(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "unknown_worker",
                "password": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_redirects_to_next_page(self):
        next_url = reverse("tasks:my-task-list")

        response = self.client.post(
            reverse("login"),
            {
                "username": self.worker.username,
                "password": self.password,
                "next": next_url,
            },
        )

        self.assertRedirects(response, next_url)
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.worker.pk),
        )

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.worker.username,
                "password": self.password,
                "next": "https://example.com/",
            },
        )

        self.assertRedirects(response, reverse("teams:team-list"))

    def test_logout_clears_session(self):
        self.client.force_login(self.worker)

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/logged_out.html")
        self.assertNotIn("_auth_user_id", self.client.session)
