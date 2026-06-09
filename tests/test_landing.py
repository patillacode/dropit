def test_landing_page_renders(client):
    res = client.get("/")
    assert res.status_code == 200


def test_upload_page_renders(client):
    res = client.get("/upload")
    assert res.status_code == 200


def test_admin_page_renders(client):
    res = client.get("/admin")
    assert res.status_code == 200


def test_files_page_renders(client):
    res = client.get("/files")
    assert res.status_code == 200


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
