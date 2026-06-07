from app.logging import configure_logging


def test_configure_logging_produces_no_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.stderr", open("/dev/null", "w"))
    configure_logging("INFO")
    import structlog

    logger = structlog.get_logger()
    logger.info("test.event", key="value")


def test_level_filter_drops_below_threshold(capsys):
    configure_logging("WARNING")
    import structlog

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
    import structlog

    logger = structlog.get_logger()
    logger.info("should.be.dropped")
    out = capsys.readouterr()
    assert "should.be.dropped" not in out.out
    assert "should.be.dropped" not in out.err
