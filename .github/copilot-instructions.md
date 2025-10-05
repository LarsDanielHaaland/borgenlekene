# 🧠 Code Instructions

## 📘 Overview
This project is a **Django-based event portal** where friends can compete across five categories:
- 🎾 Tennis  
- 🏃 Running  
- ⚽ Football  
- 🏀 Basketball  
- 🎲 Dice Game  

The goal is to provide an online platform where users can:
- Create or join an event  
- Compete in different games  
- Track results and standings  
- Eventually log in using Facebook or Google (OAuth)

The frontend currently uses **basic HTML templates** rendered by Django views, but will later evolve into a more interactive user portal.

---

## 📂 Project Structure
project_root/
├── manage.py
├── requirements.txt
├── event_portal/ # Main Django project folder
│ ├── settings.py
│ ├── urls.py
│ ├── wsgi.py
│ └── asgi.py
├── competitions/ # App for all competition-related models/views
│ ├── models.py # Models for events, players, scores
│ ├── views.py # Views for listing and joining events
│ ├── urls.py
│ ├── forms.py
│ ├── templates/competitions/ # HTML templates
│ └── tests.py
├── users/ # App for user accounts and authentication
│ ├── models.py # Custom User (optional)
│ ├── views.py # Login, registration, invitations
│ ├── urls.py
│ └── templates/users/
└── static/ # Static assets (CSS, JS, images)

yaml
Copy code

---

## 🧩 Coding Conventions
- Use **snake_case** for variables and functions.
- Use **PascalCase** for Django models.
- Each app should have its own `urls.py` file and be included in the project-level `urls.py`.
- Avoid hardcoding URLs — use `{% url 'name' %}` in templates.
- Each view should return an HTML template or JSON response (for API extensions later).

---

## 🧠 AI Guidance
When using AI tools (like ChatGPT, Copilot, Cursor):
- ✅ Do:
  - Follow Django conventions for models, views, and templates.
  - Use `django-allauth` or `social-auth-app-django` for social login.
  - Use environment variables for secrets (in `.env`).
  - Keep each competition type modular (e.g., separate models if needed).
- ❌ Don’t:
  - Hardcode sensitive info (API keys, credentials).
  - Change model fields without running migrations.
  - Replace or rename existing apps without reason.

When adding new functionality, ensure it integrates smoothly with the existing `users` and `competitions` apps.

---

## ⚙️ Setup and Execution

### Requirements
- Python 3.10+
- Django 5+
- Optional: `django-allauth` for social login  
- Optional: `python-dotenv` for environment configuration

Install dependencies:
```bash
pip install -r requirements.txt
Run the development server
bash
Copy code
python manage.py runserver
Apply migrations
bash
Copy code
python manage.py makemigrations
python manage.py migrate
Create a superuser
bash
Copy code
python manage.py createsuperuser
Then visit:
👉 http://127.0.0.1:8000/

🧪 Testing Guidelines
Each app should have its own tests.py.

Use Django’s TestCase class.

Mock authentication when testing protected views.

Prefer self-contained test data using setUp().

Example:

python
Copy code
class EventViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")

    def test_event_list_loads(self):
        response = self.client.get("/events/")
        self.assertEqual(response.status_code, 200)
🧭 Contribution Workflow
Create a new branch for each feature (e.g., feature/social-login).

Make your changes following the code conventions.

Run tests with:

bash
Copy code
python manage.py test
Commit with a clear message:

sql
Copy code
git commit -m "Add Google login using django-allauth"
Open a pull request or merge after review.

🧰 Common Tasks
Task	Command
Run the app	python manage.py runserver
Run tests	python manage.py test
Make migrations	python manage.py makemigrations
Apply migrations	python manage.py migrate
Create admin user	python manage.py createsuperuser

🔐 Future Roadmap
 Add Google/Facebook login with django-allauth

 Add user profile pages

 Implement invitation system via email link

 Add leaderboards for all 5 competitions

 Support multiple concurrent events

 Improve frontend (possibly Vue or React integration)

Would you like me to:
1. Include **instructions for setting up `django-allauth`** for Facebook/Google login right inside the markdown,  
or  
2. Keep this file focused only on project structure and conventions, and create a separate `social-login-setup.md` for OAuth setup?