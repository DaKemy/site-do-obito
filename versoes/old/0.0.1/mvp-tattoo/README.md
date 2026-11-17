# Tattoo MVP

## Running the Flask app

Set these environment variables before starting the app:

- `FLASK_SECRET_KEY`: a long, random value used to sign sessions.
- `ADMIN_USERNAME`: the administrator login.
- `ADMIN_PASSWORD`: a strong administrator password.
- `FLASK_DEBUG`: optionally set to `1` for local development only.

Do not commit real credentials, the local SQLite database, or uploaded files.
The database and uploads directory are excluded by the repository's `.gitignore`.

Install dependencies from `requirements.txt`, then run `python app.py` from this
directory.
