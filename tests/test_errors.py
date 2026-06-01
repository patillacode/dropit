from app.errors import error_response


def test_error_response_expired():
    r = error_response("Page has expired")
    assert r.status_code == 404
    assert b"This page has expired" in r.body
    assert b"The link is no longer valid." in r.body


def test_error_response_not_found():
    r = error_response("anything else")
    assert r.status_code == 404
    assert b"This page doesn't exist" in r.body
    assert b"Nothing was ever uploaded here." in r.body


def test_error_response_custom_status():
    r = error_response("anything else", status_code=410)
    assert r.status_code == 410
