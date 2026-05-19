from fastapi.testclient import TestClient
from app.core.config import settings


def test_signup(client: TestClient):
    response = client.post(
        f"{settings.API_V1_STR}/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "securepassword",
            "full_name": "New User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
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
