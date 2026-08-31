"""
Pytest configuration and shared fixtures.
Uses an in-memory SQLite database for fast, isolated tests.
No real PostgreSQL required to run the test suite.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User, UserRole

# Use in-memory SQLite for tests (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db():
    """Fresh database for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db):
    """HTTP test client with DB override."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def nurse_user(db):
    """A seeded Triage Nurse user."""
    user = User(
        staff_id="TN-0421",
        name="Sr. Priya Sharma",
        role=UserRole.TRIAGE_NURSE,
        department="Emergency",
        hashed_password=hash_password("demo123"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def clinician_user(db):
    user = User(
        staff_id="CL-0112",
        name="Dr. Anand Rajan",
        role=UserRole.CLINICIAN,
        department="Emergency",
        hashed_password=hash_password("demo123"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db):
    user = User(
        staff_id="AD-0031",
        name="Admin Suresh Nair",
        role=UserRole.ADMINISTRATOR,
        department="Administration",
        hashed_password=hash_password("demo123"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_token(client: AsyncClient, staff_id: str, password: str = "demo123") -> str:
    """Helper: login and return Bearer token."""
    resp = await client.post("/api/v1/auth/login", json={"staff_id": staff_id, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]
