from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, func, select

from app.models import Page
from app.settings import get_settings
from app.utils import utcnow

_BANNER_HEIGHT = "48px"

_BANNER_TEMPLATE = """\
<style>
@font-face {{
  font-family: 'DM Mono';
  font-style: normal;
  font-weight: 300;
  font-display: swap;
  src: url('/static/fonts/dm-mono-300.woff2') format('woff2');
}}
@font-face {{
  font-family: 'DM Mono';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/static/fonts/dm-mono-regular.woff2') format('woff2');
}}
#dropit-banner {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: {height};
  background: #09090a;
  border-bottom: 1px solid #222226;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem;
  z-index: 2147483647;
  box-sizing: border-box;
}}
#dropit-banner .db-brand {{
  color: #c8ff00;
  font-weight: 400;
  letter-spacing: 0.06em;
  text-transform: lowercase;
}}
#dropit-banner .db-tagline {{
  color: #5a5a60;
  letter-spacing: 0.04em;
  font-size: 0.72rem;
}}
#dropit-banner .db-cta {{
  color: #ece9e0;
  text-decoration: none;
  letter-spacing: 0.05em;
  font-size: 0.72rem;
  border: 1px solid #222226;
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  transition: border-color 0.2s, color 0.2s;
}}
#dropit-banner .db-cta:hover {{
  border-color: #c8ff00;
  color: #c8ff00;
}}
#dropit-spacer {{
  display: block;
  height: {height};
  width: 100%;
}}
</style>
<div id="dropit-banner">
  <span class="db-brand">drop.it</span>
  <span class="db-tagline">shared via drop.it</span>
  <a class="db-cta" href="{base_url}" target="_blank" rel="noopener">try it ↗</a>
</div>
<div id="dropit-spacer"></div>
"""


def inject_banner(html: bytes, base_url: str) -> bytes:
    snippet = _BANNER_TEMPLATE.format(height=_BANNER_HEIGHT, base_url=base_url).encode()
    lower = html.lower()
    body_pos = lower.find(b"<body")
    if body_pos == -1:
        return snippet + html
    tag_end = lower.find(b">", body_pos)
    insert_at = tag_end + 1
    return html[:insert_at] + snippet + html[insert_at:]


def serve_page_content(page_id: str, session: Session) -> HTMLResponse:
    settings = get_settings()

    page = session.exec(select(Page).where(func.lower(Page.id) == page_id.lower())).first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    if page.expires_at is not None and page.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page has expired")

    file_path = Path(settings.data_dir) / "pages" / page.id
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    content = file_path.read_bytes()
    if settings.banner_enabled:
        content = inject_banner(
            content, base_url=f"{settings.content_scheme}://{settings.content_domain}"
        )
    return HTMLResponse(content=content)
