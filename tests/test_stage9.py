from app.api import app, health


def test_fastapi_health_endpoint_contract():
    assert health() == {"status": "ok"}
    assert any(route.path == "/health" for route in app.routes)
