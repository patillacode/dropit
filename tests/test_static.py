def test_static_asset_sets_no_cache(client):
    res = client.get("/static/css/base.css")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-cache"
    assert res.headers.get("etag")


def test_static_asset_revalidates_with_etag(client):
    first = client.get("/static/css/base.css")
    etag = first.headers["etag"]
    res = client.get("/static/css/base.css", headers={"If-None-Match": etag})
    assert res.status_code == 304
