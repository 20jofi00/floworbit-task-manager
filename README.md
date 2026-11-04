# FlowOrbit

FlowOrbit helps IT teams manage tasks and projects while tracking progress.

The project is currently in development. So far, it includes a custom `Worker` user model, job positions, and Django admin pages for managing them.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)

## Local setup

Install the project dependencies:

```powershell
uv sync
```

Create a local environment file from the example:

```powershell
Copy-Item .env.example .env
```

Generate a new Django secret key:

```powershell
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated value after `DJANGO_SECRET_KEY=` in `.env`. Keep this file private and never commit it.

Apply the database migrations:

```powershell
uv run python manage.py migrate
```

Create an administrator account:

```powershell
uv run python manage.py createsuperuser
```

Start the development server:

```powershell
uv run python manage.py runserver
```

Open the admin panel at http://127.0.0.1:8000/admin/ and sign in with the administrator account.
