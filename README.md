# FlowOrbit

FlowOrbit helps IT teams manage tasks and projects while tracking progress.

Workers can organize projects, assign tasks to teammates, manage deadlines, and mark their own work as completed. Task dependencies help the team understand which work must be finished first.

## Features

Users can register, log in, and access the teams they belong to. A worker can be a member of several teams, while each project belongs to one team.

Team members can create and edit projects and tasks. Tasks support descriptions, deadlines, priorities, task types, and tags. Several workers can be assigned to the same task.

Each worker marks their own part as completed. The whole task becomes completed when all assignees have finished their work and all prerequisite tasks are completed. Adding another assignee or cancelling a completion mark can reopen the task and update dependent tasks.

Dependencies are allowed only between tasks in the same project. A task cannot depend on itself, and circular dependencies are rejected.

The My Tasks page separates the user's completed and incomplete assignments. Users can search by task name and select which teams to display. Team task lists also support filters by project, task type, tags, priority, and deadline.

Each project has a task board and a monthly deadline calendar. Team dashboards show task statistics and project progress. Workload pages show each member's completed and incomplete assignment counts.

The interface uses Bootstrap 5 and adapts to different screen sizes.

## Task statuses

Unassigned tasks have no assignees and no unfinished prerequisites. They use a white background with a neutral border.

Tasks in progress have assignees but are not completed or blocked. They are marked yellow.

Blocked tasks have at least one unfinished prerequisite. They are marked red.

Completed tasks have at least one assignee, all assignees have completed their parts, and all prerequisite tasks are completed. They are marked green.

On the dashboard, Open includes both unassigned tasks and tasks in progress. Overdue counts unfinished tasks with deadlines before today.

## Access and administration

Workers can access only the teams they belong to and the projects and tasks of those teams.

Any member of a project's team can edit its tasks and manage assignees. Workers can mark only their own assignments as completed.

Administrators manage teams, team membership, positions, task types, and tags through the Django admin panel. Positions are optional.

A newly registered worker does not belong to a team automatically. An administrator must add them before they can access a team workspace.

## Technologies

The project uses Python, Django, PostgreSQL in production, SQLite for local development, and Bootstrap 5.

Forms are displayed using django-crispy-forms and crispy-bootstrap5. Environment variables are loaded with python-dotenv. Dependencies are managed with uv.

## Requirements

Install Python 3.13 or newer, Git, and [uv](https://docs.astral.sh/uv/getting-started/installation/).

An internet connection is needed to load Bootstrap from its CDN.

## Installation

Clone the develop branch and open the project directory:

```bash
git clone --branch develop https://github.com/20jofi00/floworbit-task-manager.git
cd floworbit-task-manager
```

Install the dependencies:

```bash
uv sync
```

Create a local environment file from the example.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Generate a Django secret key:

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Open `.env` and paste the generated key inside quotes:

```dotenv
DJANGO_SECRET_KEY="paste-generated-key-here"
```

The `.env` file is excluded from Git.

Apply the database migrations:

```bash
uv run python manage.py migrate
```

Create an administrator account:

```bash
uv run python manage.py createsuperuser
```

Start the development server:

```bash
uv run python manage.py runserver
```

Open the app at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

The admin panel is available at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## Getting started

Register a worker account on the signup page.

Then sign in to the admin panel using the administrator account. Create a team and add the worker to its members. Create at least one task type. You can also add positions and tags.

Sign in as the worker, open the team, and create a project. Add tasks to the project and assign teammates through each task's Participants page.

## Running tests

Run the complete test suite:

```bash
uv run python manage.py test
```

You can also run tests for a specific application:

```bash
uv run python manage.py test accounts
uv run python manage.py test projects
uv run python manage.py test teams
uv run python manage.py test tasks
```

Run Django's system checks:

```bash
uv run python manage.py check
```

## Project structure

The accounts application contains workers, positions, and registration.

The teams application handles team membership, dashboards, and workload pages.

The projects application handles projects, their forms, and project progress.

The tasks application handles tasks, assignments, dependencies, filters, task boards, and calendars.

## Settings and deployment

Shared settings are in `config/settings/base.py`. Local commands use
`config.settings.dev`. WSGI and ASGI entry points use `config.settings.prod`.

For production, set `DJANGO_DEBUG=false`, provide a new random
`DJANGO_SECRET_KEY`, and list the real hostnames in `DJANGO_ALLOWED_HOSTS`.
Configure the database through the `DJANGO_DB_*` variables in `.env.example`.
SQLite is supported by default; another database engine requires its driver.

Configure SMTP using the `DJANGO_EMAIL_*` variables and set a real sender in
`DJANGO_DEFAULT_FROM_EMAIL`. Development continues to use console email.

Check production settings and collect static files:

```bash
uv run python manage.py check --deploy --settings=config.settings.prod
uv run python manage.py collectstatic --noinput --settings=config.settings.prod
```

Serve the collected `staticfiles` directory with the hosting platform or web
server. Run a production WSGI or ASGI server; Django's `runserver` is for local
development. Apply migrations against the configured production database
before starting the app.

Production redirects HTTP to HTTPS and requires secure session and CSRF
cookies. HSTS defaults to one hour for the current hostname. Enable
`DJANGO_HSTS_INCLUDE_SUBDOMAINS` only after confirming HTTPS on all subdomains.
Enable `DJANGO_HSTS_PRELOAD` only when deliberately preparing for preload.
Until then, Django may report `security.W005` and `security.W021`; those
checks are not silenced.

Leave `DJANGO_TRUST_PROXY_HEADERS=false` unless your trusted reverse proxy
removes client-supplied `X-Forwarded-Proto` and sets the correct value itself.

My Tasks has separate pagination for incomplete and completed assignments,
with up to 20 tasks in each section. Each section keeps its own page number,
and both preserve the selected search and teams.

Project boards show 40 tasks per page. Calendars show up to 100 tasks from
the selected month per page. Board columns and calendar cells contain only
the tasks on the current page. Pagination preserves the relevant filters
and selected calendar month.

## Live demo

Visit [FlowOrbit](https://floworbit.onrender.com).

Demo account:

- Username: `alex.morgan`
- Password: `OrbitDemo!2026`

The demo runs on Render's free plan, so the first visit after inactivity may take about a minute to load.
