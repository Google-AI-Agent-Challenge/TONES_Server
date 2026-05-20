import uuid
from fastapi.testclient import TestClient
from app.core.config import settings


def test_signup(client: TestClient):
    random_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        f"{settings.API_V1_STR}/auth/signup",
        json={
            "email": random_email,
            "password": "securepassword",
            "full_name": "New User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == random_email
    assert "id" in data



def test_login_access_token(client: TestClient):
    # UserService에 더미용으로 등록된 test@example.com / testpassword 계정 테스트
    response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
