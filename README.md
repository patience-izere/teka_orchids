# Teka Platform

Lightweight README for local development and running tests.

## Quickstart (Linux/macOS)

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Set environment variables (for development)

```bash
# Use the Django settings module
export DJANGO_SETTINGS_MODULE=teka_platform.settings
# Optional: use Redis for Channels (if running Redis locally)
# export USE_REDIS=1
```

4. Apply migrations and create a superuser

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

5. Run tests

```bash
python3 manage.py test
```

6. Run the development server

```bash
# For WSGI (regular Django dev server)
python3 manage.py runserver

# For ASGI (if you plan to use Channels/daphne)
# daphne teka_platform.asgi:application
```

Notes
- The project includes a Channels in-memory fallback when `USE_REDIS` is not set, so tests and local dev don't require Redis by default.
- `requirements.txt` contains development and test dependencies (Black, Ruff, pytest-django, etc.).
- For CI, add a workflow to install requirements and run `python3 manage.py test`.

Troubleshooting
- If you see `Invalid HTTP_HOST header: 'testserver'`, ensure `ALLOWED_HOSTS` in `teka_platform/settings.py` allows the host used in tests, or run tests without overriding the host.
- If Channels needs Redis in production, set `USE_REDIS=1` and run a Redis instance accessible at `127.0.0.1:6379` or configure `CHANNEL_LAYERS` accordingly.

License: MIT (change as needed)
