# Borgenlekene

Borgenlekene is a Django event portal for organizing a full activity day with friends. Participants can compete across tennis, running, football, basketball, and dice games, with results collected into a shared leaderboard.

The project started from a simple idea: gather friends for a day of activities and competition before going out together afterward.

## Features

- Event creation with date and start time
- Event invitations
- User registration and login
- Optional Facebook login
- Participant and nickname management
- Tennis, running, football, basketball, and dice activities
- Live running timer
- Results, rankings, and total scores
- PostgreSQL support through Supabase
- Production static files served with WhiteNoise

## Project Layout

```text
mymobilesite/
  manage.py
  core/                 Main application, models, views, tests, and game JavaScript
  project/              Canonical Django settings, URLs, WSGI, and ASGI configuration
  templates/            Django templates
  static/               Shared static assets
requirements.txt        Python dependencies
```

## Local Development

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repository root:

```env
SECRET_KEY=local-development-secret
DEBUG=True
DATABASE_URL=
```

When `DATABASE_URL` is empty, local development uses SQLite at `mymobilesite/db.sqlite3`.

Run migrations and start the development server:

```bash
cd mymobilesite
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser.

## Testing

Run the focused Django test suites:

```bash
venv/bin/python mymobilesite/manage.py test \
  core.tests.test_activity_points \
  core.tests.test_auth_signup \
  core.tests.test_basketball_smoke \
  core.tests.test_claim_nickname \
  core.tests.test_portal_invitations \
  core.tests.test_tennis \
  core.tests.test_tennis_points \
  core.tests.test_tournament_api
```

Run Django system checks:

```bash
venv/bin/python mymobilesite/manage.py check
```

## Supabase Database

The application uses SQLite locally unless `DATABASE_URL` is set. When `DATABASE_URL` is present, Django connects to PostgreSQL, including an existing Supabase database.

Use the PostgreSQL connection string from Supabase. Keep the password private and never commit it to Git.

```env
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
```

Apply migrations to the configured database with:

```bash
python mymobilesite/manage.py migrate
```

## Render Deployment

Create a Render Web Service connected to this repository. Leave **Root Directory** empty because the Django project is inside `mymobilesite/`.

### Build Command

```bash
pip install -r requirements.txt && python mymobilesite/manage.py collectstatic --no-input
```

### Start Command

```bash
python mymobilesite/manage.py migrate && gunicorn --chdir mymobilesite project.wsgi:application
```

### Required Environment Variables

```env
SECRET_KEY=<long-random-production-secret>
DEBUG=False
DATABASE_URL=<Supabase PostgreSQL connection string>
ALLOWED_HOSTS=<your-service>.onrender.com
CSRF_TRUSTED_ORIGINS=https://<your-service>.onrender.com
```

`RENDER_EXTERNAL_HOSTNAME` is provided automatically by Render and is also supported by the Django settings.

Use a separate Supabase project or database for staging/testing. Do not use the production database for test data.

## Static Files

Static files are collected into `mymobilesite/staticfiles/` and served by WhiteNoise in production:

```bash
python mymobilesite/manage.py collectstatic --no-input
```

The generated `staticfiles/` directory is ignored by Git.

## Security Notes

- Never commit `.env`, database URLs, passwords, API keys, or OAuth secrets.
- Use a unique, long `SECRET_KEY` in production.
- Keep `DEBUG=False` in Render.
- Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for the deployed hostname.
- Run migrations against the intended database before using the deployed application.
