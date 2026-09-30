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


def test_swagger_openapi_uses_korean_service_and_endpoint_descriptions() -> None:
    schema = TestClient(app).get("/openapi.json").json()

    assert schema["info"]["title"] == "UXFlow Agent API"
    assert "한국어" in schema["info"]["description"]
    assert schema["paths"]["/api/designs/plan"]["post"]["summary"] == "화면 계획 생성"


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


def test_figma_status_only_reports_whether_a_token_is_configured(
    monkeypatch,
) -> None:
    """The API must never include the secret itself in its response."""
    monkeypatch.setattr("app.routers.designs.figma_token_configured", lambda: True)

    response = TestClient(app).get("/api/figma/status")

    assert response.status_code == 200
    assert response.json() == {"configured": True}


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


def test_review_rejects_recommendation_for_a_different_plan() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    plan = client.post("/api/designs/plan", json=REQUEST).json()
    recommendation = client.post("/api/designs/recommend-components", json=plan).json()
    recommendation["page_ids"] = ["other", "other-complete"]
    recommendation["page_components"][0]["page_id"] = "other"
    recommendation["page_components"][1]["page_id"] = "other-complete"

    response = client.post(
        "/api/designs/review",
        json={"plan": plan, "recommendation": recommendation},
    )

    assert response.status_code == 422


def test_run_lookup_returns_trace() -> None:
    client = TestClient(app)
    run = client.post("/api/designs/run", json=REQUEST).json()
    response = client.get(f"/api/designs/{run['run_id']}")

    assert response.status_code == 200
    assert "planner:verified" in response.json()["trace"]
    assert response.json()["build"]["status"] == "skipped"
