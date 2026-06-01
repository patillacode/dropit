from pathlib import Path

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=True,
)

_MESSAGES: dict[str, tuple[str, str]] = {
    "Page has expired": ("This page has expired", "The link is no longer valid."),
}
_DEFAULT = ("This page doesn't exist", "Nothing was ever uploaded here.")


def error_response(detail: str, status_code: int = 404) -> HTMLResponse:
    title, subtitle = _MESSAGES.get(detail, _DEFAULT)
    html = _env.get_template("error.html").render(title=title, subtitle=subtitle)
    return HTMLResponse(content=html, status_code=status_code)
