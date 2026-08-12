import os

import pytest


os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTH_SECRET"] = "integration-test-secret-with-more-than-32-characters"
os.environ["ADMIN_USER_IDS"] = "1"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from db.db import engine  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


def authenticate(client: TestClient, user_id: int, password: str = "password123"):
    response = client.post(
        "/createUser",
        json={"id": user_id, "name": f"User {user_id}", "password": password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

