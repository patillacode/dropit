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
    return html[: tag_end + 1] + snippet + html[tag_end + 1 :]
