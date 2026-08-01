def test_health(unauthenticated_client):
    response = unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
