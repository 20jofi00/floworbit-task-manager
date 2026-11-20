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

The project uses Python, Django, SQLite, and Bootstrap 5.

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
