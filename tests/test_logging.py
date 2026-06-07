import structlog

from app.logging import configure_logging


def test_configure_logging_produces_no_error(monkeypatch):
    monkeypatch.setattr("sys.stderr", open("/dev/null", "w"))
    configure_logging("INFO")
    logger = structlog.get_logger()
    logger.info("test.event", key="value")


def test_level_filter_drops_below_threshold(capsys):
    configure_logging("WARNING")
    logger = structlog.get_logger()
    logger.info("should.be.dropped")
    logger.warning("should.appear")
    out = capsys.readouterr().out
    assert "should.be.dropped" not in out
    assert "should.appear" in out


def test_configure_logging_accepts_log_level():
    configure_logging("ERROR")
    configure_logging("INFO")


def test_level_filter_drops_event_via_processor(capsys):
    configure_logging("WARNING")
    logger = structlog.get_logger()
    logger.info("should.be.dropped")
    out = capsys.readouterr()
    assert "should.be.dropped" not in out.out
    assert "should.be.dropped" not in out.err


def test_request_id_bound_per_request(client):
    from unittest.mock import patch
    bound = {}

    original_bind = structlog.contextvars.bind_contextvars

    def capturing_bind(**kw):
        bound.update(kw)
        return original_bind(**kw)

    with patch("structlog.contextvars.bind_contextvars", side_effect=capturing_bind):
        client.get("/health")

    assert "request_id" in bound
    rid = bound["request_id"]
    assert isinstance(rid, str) and len(rid) == 8
