from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


def parse_ttl_duration(ttl: str) -> int | None:
    if ttl == "forever":
        return None
    if ttl.endswith("h"):
        return int(ttl[:-1]) * 3600
    if ttl.endswith("d"):
        return int(ttl[:-1]) * 86400
    raise ValueError(f"Invalid TTL format: {ttl!r}. Use e.g. '24h', '7d', or 'forever'.")


class Settings(BaseSettings):
    allowed_ttls: str = "1h,6h,24h,48h,7d"
    default_ttl: str = "24h"
    max_user_ttl: str = "24h"
    max_upload_size: int = 5_242_880
    cleanup_interval_hours: int = 1
    data_dir: str = "./data"
    content_domain: str = "localhost:8000"
    admin_token: str | None = None
    log_level: str = "INFO"
    banner_enabled: bool = True

    @model_validator(mode="after")
    def _validate_ttls(self) -> "Settings":
        for ttl in self.ttl_list:
            parse_ttl_duration(ttl)
        parse_ttl_duration(self.default_ttl)
        parse_ttl_duration(self.max_user_ttl)
        return self

    @property
    def content_scheme(self) -> str:
        return "http" if self.content_domain.split(":")[0] == "localhost" else "https"

    def page_url(self, page_id: str) -> str:
        return f"{self.content_scheme}://{page_id}.{self.content_domain}"

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
