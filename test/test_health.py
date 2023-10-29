
# import test_docs.py

from schema import HealthCheck


def test_healthcheck(test_app):
    response = test_app.get("/health")
    assert response.status_code == 200
    health = HealthCheck(**response.json())
    assert health.status == "OK"
