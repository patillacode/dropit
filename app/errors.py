from pathlib import Path

from fastapi.responses import HTMLResponse

_ERROR_HTML = (Path(__file__).parent / "static" / "error.html").read_text()

_MESSAGES: dict[str, tuple[str, str]] = {
    "Page has expired": ("This page has expired", "The link is no longer valid."),
}
_DEFAULT = ("This page doesn't exist", "Nothing was ever uploaded here.")


def error_response(detail: str, status_code: int = 404) -> HTMLResponse:
    title, subtitle = _MESSAGES.get(detail, _DEFAULT)
    html = _ERROR_HTML.replace("__TITLE__", title).replace("__SUBTITLE__", subtitle)
    return HTMLResponse(content=html, status_code=status_code)
