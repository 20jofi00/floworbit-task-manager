from django.urls import path

from accounts.views import WorkerRegistrationView

app_name = "accounts"

urlpatterns = [
    path("signup/", WorkerRegistrationView.as_view(), name="signup"),
]
