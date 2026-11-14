# Tattoo MVP

## Running the Flask app

The app loads these environment variables from `.env` in the project root:

- `FLASK_SECRET_KEY`: a long, random value used to sign sessions.
- `ADMIN_USERNAME`: the administrator login.
- `ADMIN_PASSWORD`: a strong administrator password.
- `FLASK_DEBUG`: optionally set to `1` for local development only.

Do not commit real credentials, the local SQLite database, or uploaded files.
The database and uploads directory are excluded by the repository's `.gitignore`.

Install dependencies from `requirements.txt`, then double-click `app.py` to
start the site and open it in your browser at `http://127.0.0.1:5000`. Keep the
terminal window open while using the site; close it to stop the server. Startup
errors stay visible in the terminal.
