from django.contrib.auth import login
from django.views import generic
from django.shortcuts import redirect


from accounts.forms import WorkerRegistrationForm


class WorkerRegistrationView(generic.CreateView):
    form_class = WorkerRegistrationForm
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save()
        login(request=self.request, user=user)
        return redirect("teams:team-list")
