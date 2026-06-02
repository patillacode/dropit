def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "User-agent: *" in r.text
    assert "Allow: /$" in r.text
    assert "Disallow: /admin" in r.text
    assert "Disallow: /me" in r.text
    assert "Disallow: /upload" in r.text
    assert "Disallow: /static/" in r.text
