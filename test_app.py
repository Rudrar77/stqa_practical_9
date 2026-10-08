import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from app import create_app


class TodoAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": os.path.join(self.temp_dir.name, "test.sqlite"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def register(self, username="alice", password="password123"):
        return self.client.post(
            "/register",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_registration_creates_account_and_logs_in(self):
        response = self.register()
        self.assertIn(b"alice", response.data)
        self.assertIn(b"Your tasks", response.data)

    def test_registration_rejects_short_password(self):
        response = self.client.post(
            "/register",
            data={"username": "alice", "password": "short"},
            follow_redirects=True,
        )
        self.assertIn(b"at least 8 characters", response.data)
        self.assertNotIn(b"Your tasks", response.data)

    def test_duplicate_username_is_rejected(self):
        self.register()
        self.client.post(
            "/logout",
            follow_redirects=True,
        )
        response = self.register()
        self.assertIn(b"already registered", response.data)

    def test_login_and_logout(self):
        self.register()
        self.client.post("/logout")
        response = self.client.post(
            "/login",
            data={"username": "alice", "password": "password123"},
            follow_redirects=True,
        )
        self.assertIn(b"Your tasks", response.data)
        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn(b"Create account", response.data)

    def test_user_can_add_complete_and_delete_task(self):
        self.register()
        response = self.client.post(
            "/todos", data={"title": "Write tests"}, follow_redirects=True
        )
        self.assertIn(b"Write tests", response.data)

        with closing(sqlite3.connect(self.app.config["DATABASE"])) as db:
            todo_id = db.execute(
                "SELECT id FROM todos WHERE title = ?", ("Write tests",)
            ).fetchone()[0]

        response = self.client.post(
            f"/todos/{todo_id}/toggle", follow_redirects=True
        )
        self.assertIn(b"is-complete", response.data)
        response = self.client.post(
            f"/todos/{todo_id}/delete", follow_redirects=True
        )
        self.assertNotIn(b"Write tests", response.data)

    def test_tasks_are_private_to_each_user(self):
        self.register("alice")
        self.client.post("/todos", data={"title": "Alice task"})
        self.client.post("/logout")
        self.register("bob")
        response = self.client.get("/")
        self.assertNotIn(b"Alice task", response.data)

    def test_task_routes_require_login(self):
        response = self.client.post(
            "/todos", data={"title": "Do not add"}, follow_redirects=True
        )
        self.assertIn(b"Create account", response.data)
        self.assertNotIn(b"Do not add", response.data)


if __name__ == "__main__":
    unittest.main()
