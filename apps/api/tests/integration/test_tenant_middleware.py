def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_meta_ops_token(client, ops_headers):
    r = client.get("/api/v1/meta", headers=ops_headers)
    assert r.status_code == 200


def test_overview_anon(client):
    r = client.get("/api/v1/overview")
    assert r.status_code >= 400