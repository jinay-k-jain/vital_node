"""
Authentication tests.
Covers: login, logout, /me, role enforcement, wrong credentials.
"""
import pytest
from tests.conftest import get_token


@pytest.mark.asyncio
async def test_login_success(client, nurse_user):
    resp = await client.post("/api/v1/auth/login", json={"staff_id": "TN-0421", "password": "demo123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "Triage Nurse"
    assert data["user"]["staffId"] == "TN-0421"


@pytest.mark.asyncio
async def test_login_wrong_password(client, nurse_user):
    resp = await client.post("/api/v1/auth/login", json={"staff_id": "TN-0421", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_login_unknown_user(client, nurse_user):
    resp = await client.post("/api/v1/auth/login", json={"staff_id": "XX-9999", "password": "demo123"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_empty_staff_id(client, nurse_user):
    resp = await client.post("/api/v1/auth/login", json={"staff_id": "", "password": "demo123"})
    assert resp.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_me_authenticated(client, nurse_user):
    token = await get_token(client, "TN-0421")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["staffId"] == "TN-0421"
    assert data["role"] == "Triage Nurse"


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, nurse_user):
    token = await get_token(client, "TN-0421")
    resp = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "message" in resp.json()


@pytest.mark.asyncio
async def test_admin_endpoint_rejected_for_nurse(client, nurse_user):
    """Nurse must receive HTTP 403 on admin-only endpoint."""
    token = await get_token(client, "TN-0421")
    resp = await client.get("/api/v1/system/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_endpoint_allowed_for_admin(client, admin_user):
    token = await get_token(client, "AD-0031")
    resp = await client.get("/api/v1/system/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_unauthenticated(client):
    """Health endpoint must be accessible without auth."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "api" in data
    assert data["api"] == "ok"
