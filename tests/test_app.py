from copy import deepcopy

import httpx
import pytest
import pytest_asyncio

from src.app import activities, app


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_get_activities_returns_activity_details(client):
    response = await client.get("/activities")

    assert response.status_code == 200
    chess_club = response.json()["Chess Club"]
    assert chess_club["description"]
    assert chess_club["schedule"]
    assert chess_club["max_participants"] == 12
    assert "michael@mergington.edu" in chess_club["participants"]


@pytest.mark.asyncio
async def test_signup_adds_participant(client):
    email = "new.student@mergington.edu"

    response = await client.post(
        "/activities/Soccer Club/signup", params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for Soccer Club"
    }
    activities_response = await client.get("/activities")
    assert email in activities_response.json()["Soccer Club"]["participants"]


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_participant(client):
    response = await client.post(
        "/activities/Chess Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


@pytest.mark.asyncio
async def test_signup_rejects_unknown_activity(client):
    response = await client.post(
        "/activities/Unknown Club/signup",
        params={"email": "new.student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


@pytest.mark.asyncio
async def test_unregister_removes_participant(client):
    email = "michael@mergington.edu"

    response = await client.delete(
        "/activities/Chess Club/participants", params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from Chess Club"
    }
    activities_response = await client.get("/activities")
    assert email not in activities_response.json()["Chess Club"]["participants"]


@pytest.mark.asyncio
async def test_unregister_rejects_nonparticipant(client):
    response = await client.delete(
        "/activities/Soccer Club/participants",
        params={"email": "not.enrolled@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


@pytest.mark.asyncio
async def test_unregister_rejects_unknown_activity(client):
    response = await client.delete(
        "/activities/Unknown Club/participants",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"