import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-development-key"),
        DATABASE=str(Path(app.instance_path) / "todo.sqlite"),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        db.commit()

    def login_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if "user_id" not in session:
                return redirect(url_for("index"))
            return view(**kwargs)

        return wrapped_view

    @app.route("/")
    def index():
        todos = []
        if "user_id" in session:
            todos = get_db().execute(
                "SELECT id, title, completed FROM todos "
                "WHERE user_id = ? ORDER BY id DESC",
                (session["user_id"],),
            ).fetchall()
        return render_template("index.html", todos=todos)

    @app.post("/register")
    def register():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Enter a username and password.", "error")
            return redirect(url_for("index"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("index"))

        db = get_db()
        try:
            cursor = db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("That username is already registered.", "error")
            return redirect(url_for("index"))

        session.clear()
        session["user_id"] = cursor.lastrowid
        session["username"] = username
        return redirect(url_for("index"))

    @app.post("/login")
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect username or password.", "error")
            return redirect(url_for("index"))

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.post("/todos")
    @login_required
    def add_todo():
        title = request.form.get("title", "").strip()
        if not title:
            flash("A task cannot be empty.", "error")
        elif len(title) > 120:
            flash("Tasks must be 120 characters or fewer.", "error")
        else:
            db = get_db()
            db.execute(
                "INSERT INTO todos (user_id, title) VALUES (?, ?)",
                (session["user_id"], title),
            )
            db.commit()
        return redirect(url_for("index"))

    @app.post("/todos/<int:todo_id>/toggle")
    @login_required
    def toggle_todo(todo_id):
        db = get_db()
        db.execute(
            "UPDATE todos SET completed = CASE completed WHEN 0 THEN 1 ELSE 0 END "
            "WHERE id = ? AND user_id = ?",
            (todo_id, session["user_id"]),
        )
        db.commit()
        return redirect(url_for("index"))

    @app.post("/todos/<int:todo_id>/delete")
    @login_required
    def delete_todo(todo_id):
        db = get_db()
        db.execute(
            "DELETE FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, session["user_id"]),
        )
        db.commit()
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
