async def test_root_identifies_the_service(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert r.json() == {"service": "PropCheck API", "status": "ok"}


async def test_health_is_served_with_and_without_the_api_prefix(client):
    for path in ("/health", "/api/health"):
        r = await client.get(path)
        assert r.status_code == 200, path
        assert r.json() == {"status": "ok"}
