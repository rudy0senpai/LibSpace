import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-for-libsphere-tests-32chars"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as backend  # noqa: E402
from models import RoleType, User  # noqa: E402


class FakeQuery:
    def __init__(self, user):
        self.user = user
        self.filters = None

    def filter(self, *criteria):
        self.filters = criteria
        return self

    def first(self):
        return self.user

    def all(self):
        return [self.user] if self.user is not None else []


class AuthApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_context = backend.app.app_context()
        cls.app_context.push()
        backend.app.config.update(TESTING=True, JWT_SECRET_KEY="test-only-secret-key-for-libsphere-tests-32chars")
        backend.db.create_all()
        department = backend.Department(code="TEST", name="Test Department", short_name="Test")
        backend.db.session.add(department)
        backend.db.session.flush()
        cls.real_accounts = [
            ("Urvashi", "25EMCAD016", "STUDENT", RoleType.STUDENT, "urvashi@libsphere.test"),
            ("Yashdeep", "25TECAD016", "FACULTY", RoleType.FACULTY, "yashdeep@libsphere.test"),
            ("Dhruv", "25DMCAD016", "DEPARTMENT", RoleType.DEPARTMENT, "dhruv@libsphere.test"),
            ("Sphere", "25LIB016", "LIBRARIAN", RoleType.LIBRARIAN, "sphere@libsphere.test"),
        ]
        for name, identifier, _public_role, role, email in cls.real_accounts:
            backend.db.session.add(User(
                name=name,
                email=email,
                password_hash="not-used-by-prototype-login",
                role=role,
                department_id=None if role == RoleType.LIBRARIAN else department.id,
                enrollment_id=identifier if role == RoleType.STUDENT else None,
                employee_id=identifier if role != RoleType.STUDENT else None,
            ))
        backend.db.session.commit()

    @classmethod
    def tearDownClass(cls):
        backend.db.session.remove()
        backend.db.drop_all()
        cls.app_context.pop()

    def setUp(self):
        backend.app.config.update(TESTING=True, JWT_SECRET_KEY="test-only-secret-key-for-libsphere-tests-32chars")
        self.client = backend.app.test_client()
        self.user = SimpleNamespace(
            id="30000000-0000-0000-0000-000000000001",
            name="Aarav Mehta",
            email="aarav.mehta@mitrc.ac.in",
            role=RoleType.STUDENT,
            department_id="00000000-0000-0000-0000-000000000001",
            is_active=True,
        )

    def test_database_backed_login_and_me_for_each_public_role(self):
        for name, identifier, public_role, stored_role, _email in self.real_accounts:
            with self.subTest(role=public_role):
                response = self.client.post("/api/auth/login", json={
                    "name": name, "user_id": identifier,
                    "role": "Teacher" if public_role == "FACULTY" else public_role,
                })
                self.assertEqual(response.status_code, 200, response.get_json())
                data = response.get_json()["data"]
                self.assertEqual(data["user"]["role"], stored_role.value)
                self.assertEqual(data["user"]["name"], name)
                self.assertIn("access_token", data)
                me = self.client.get("/api/auth/me", headers={
                    "Authorization": f"Bearer {data['access_token']}"
                })
                self.assertEqual(me.status_code, 200)
                self.assertEqual(me.get_json()["data"]["role"], stored_role.value)

    def test_postgresql_models_use_schema_enum_types(self):
        self.assertEqual(User.role.type.name, "role_type")
        self.assertTrue(User.role.type.native_enum)

    def test_login_uses_database_enrollment_id_and_returns_token_contract(self):
        response = self.client.post("/api/auth/login", json={
            "name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"
        })
        self.assertEqual(response.status_code, 200)
        body = response.get_json()["data"]
        self.assertTrue(body["access_token"])
        self.assertEqual(body["user"]["name"], "Urvashi")
        self.assertEqual(body["user"]["role"], "STUDENT")

    def test_teacher_role_maps_to_faculty_and_uses_employee_id(self):
        response = self.client.post("/api/auth/login", json={
            "name": "Yashdeep", "user_id": "25TECAD016", "role": "Teacher"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["user"]["role"], "FACULTY")

    def test_mismatched_name_or_identifier_does_not_authenticate(self):
        with patch.object(backend.db.session, "query", return_value=FakeQuery(None)):
            response = self.client.post("/api/auth/login", json={
                "name": "Not Aarav", "user_id": "MITRC25CSE001", "role": "STUDENT"
            })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_IDENTITY")

    def test_public_login_rejects_admin_role(self):
        with patch.object(backend.db.session, "query") as query:
            response = self.client.post("/api/auth/login", json={
                "name": "System Administrator", "user_id": "MITRC-ADM-001", "role": "ADMIN"
            })
        self.assertEqual(response.status_code, 401)
        query.assert_not_called()

    def test_passwordless_demo_login_is_disabled_outside_testing_mode(self):
        previous_env = backend.app.config.get("APP_ENV")
        backend.app.config["APP_ENV"] = "production"
        try:
            response = self.client.post("/api/auth/login", json={
                "name": "Urvashi", "user_id": "25EMCAD016", "role": "STUDENT"
            })
        finally:
            backend.app.config["APP_ENV"] = previous_env
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "MISSING_CREDENTIALS")

    def test_testing_login_rejects_normal_email_password_payload(self):
        response = self.client.post("/api/auth/login", json={
            "email": "urvashi@libsphere.test", "password": "not-a-testing-credential"
        })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_IDENTITY")

    def test_disabled_accounts_cannot_restore_sessions(self):
        self.user.is_active = False
        with backend.app.app_context():
            token = backend.create_access_token(identity=self.user.id)
        with patch.object(backend.db.session, "get", return_value=self.user):
            response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "ACCOUNT_DISABLED")

    def test_department_dashboard_uses_authenticated_departments_scope(self):
        account = SimpleNamespace(
            id=self.user.id, role=RoleType.DEPARTMENT,
            department_id="00000000-0000-0000-0000-000000000001", is_active=True
        )
        with backend.app.app_context():
            token = backend.create_access_token(identity=account.id)
        with patch.object(backend.db.session, "get", return_value=account), patch.object(
            backend, "get_department_dashboard_data", return_value={"scope": {"id": account.department_id}}
        ) as dashboard:
            response = self.client.get(
                "/api/reports/department/dashboard?department_id=another-department",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(response.status_code, 200)
        dashboard.assert_called_once()
        self.assertEqual(dashboard.call_args.args[0], account.department_id)

    def test_token_me_endpoint_restores_user_from_database(self):
        with backend.app.app_context():
            token = backend.create_access_token(identity=self.user.id)
        with patch.object(backend.db.session, "get", return_value=self.user):
            response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["id"], self.user.id)

    def test_health_endpoint_checks_database_and_reports_status(self):
        with patch.object(backend.db.session, "execute") as execute:
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["database"], "ok")
        execute.assert_called_once()

    def test_protected_api_without_token_returns_json_401(self):
        response = self.client.get("/api/reports/department/dashboard")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "MISSING_AUTHORIZATION")


class LocalDatabaseConfigurationTests(unittest.TestCase):
    def test_development_defaults_to_sqlite_without_postgres_env(self):
        env = os.environ.copy()
        env.pop("DATABASE_URL", None)
        env.pop("TEST_DATABASE_URL", None)
        env.pop("PYTHONPATH", None)
        env["APP_ENV"] = "development"
        result = subprocess.run(
            [sys.executable, "-c", "from config import Config; print(Config.SQLALCHEMY_DATABASE_URI)"],
            cwd=Path(__file__).resolve().parents[1] / "backend",
            env=env, capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "sqlite:///libsphere.db")


if __name__ == "__main__":
    unittest.main()
