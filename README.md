# Little List: registration, login, and to-do app

This sample web app lets a user register, log in, and manage a private list of
tasks. It uses Flask and SQLite, and includes automated tests for the account
and task flows.

## Run locally

From this folder, create and activate a virtual environment, then install the
dependencies:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Set a secret key before running the development server:

```powershell
$env:SECRET_KEY = "replace-this-with-a-random-secret"
python app.py
```

Open <http://127.0.0.1:5000>. Create an account with a password of at least
eight characters, then add, complete, or remove tasks. The SQLite database is
created automatically in the `instance` folder.

Run the tests locally with:

```text
python -m unittest discover -v
```

## Continuous testing

The GitHub Actions workflow at `.github/workflows/continuous-testing.yml`
installs the requirements and runs the tests for every push and pull request.
GitHub Copilot can help write and improve the app and tests; GitHub Actions is
what automatically runs the test pipeline.
