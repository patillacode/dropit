from functools import lru_cache

from pydantic_settings import BaseSettings


def parse_tokens(raw: str) -> dict[str, str]:
    result = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            name, token = entry.split(":", 1)
            result[token.strip()] = name.strip()
        else:
            result[entry] = entry
    return result


def parse_ttl_duration(ttl: str) -> int | None:
    if ttl == "forever":
        return None
    if ttl.endswith("h"):
        return int(ttl[:-1]) * 3600
    if ttl.endswith("d"):
        return int(ttl[:-1]) * 86400
    raise ValueError(f"Invalid TTL format: {ttl!r}. Use e.g. '24h', '7d', or 'forever'.")


class Settings(BaseSettings):
    upload_tokens: str
    allowed_ttls: str = "1h,6h,24h,48h,7d"
    default_ttl: str = "24h"
    max_user_ttl: str = "24h"
    max_upload_size: int = 5_242_880
    cleanup_interval_hours: int = 1
    data_dir: str = "./data"
    base_url: str = "http://localhost:8000"
    content_domain: str = "localhost:8000"
    admin_token: str | None = None

    @property
    def content_scheme(self) -> str:
        return "http" if self.content_domain.split(":")[0] == "localhost" else "https"

    def page_url(self, page_id: str) -> str:
        return f"{self.content_scheme}://{page_id}.{self.content_domain}"

    @property
    def token_map(self) -> dict[str, str]:
        return parse_tokens(self.upload_tokens)

    @property
    def ttl_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_ttls.split(",")]

    @property
    def user_ttl_list(self) -> list[str]:
        max_secs = parse_ttl_duration(self.max_user_ttl)
        result = []
        for t in self.ttl_list:
            secs = parse_ttl_duration(t)
            if secs is not None and max_secs is not None and secs <= max_secs:
                result.append(t)
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
