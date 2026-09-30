from fastapi.testclient import TestClient
from app.main import app


REQUEST = {
    "service_name": "예약",
    "target_users": ["여행자"],
    "primary_user_goal": "예약 완료",
    "required_features": ["검색"],
    "platforms": ["web"],
}


def test_health_returns_service_name() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "UXFlow Agent"}


def test_plan_endpoint_returns_page_count() -> None:
    response = TestClient(app).post("/api/designs/plan", json=REQUEST)

    assert response.status_code == 200
    assert response.json()["page_count"] == 2


def test_empty_required_features_is_rejected_before_agent_runs() -> None:
    response = TestClient(app).post(
        "/api/designs/plan", json={**REQUEST, "required_features": []}
    )

    assert response.status_code == 422


def test_contracts_endpoint_lists_page_plan() -> None:
    response = TestClient(app).get("/api/contracts")

    assert response.status_code == 200
    assert "PagePlan" in response.json()


def test_recommend_and_review_endpoints_return_valid_handoffs() -> None:
    client = TestClient(app)
    plan = client.post("/api/designs/plan", json=REQUEST).json()
    recommendation = client.post("/api/designs/recommend-components", json=plan).json()

    response = client.post(
        "/api/designs/review",
        json={"plan": plan, "recommendation": recommendation},
    )

    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_run_lookup_returns_trace() -> None:
    client = TestClient(app)
    run = client.post("/api/designs/run", json=REQUEST).json()
    response = client.get(f"/api/designs/{run['run_id']}")

    assert response.status_code == 200
    assert "planner:verified" in response.json()["trace"]
    assert response.json()["build"]["status"] == "skipped"
