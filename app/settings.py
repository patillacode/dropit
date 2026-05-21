from functools import lru_cache

from pydantic_settings import BaseSettings


def parse_tokens(raw: str) -> dict[str, str]:
    """Return {token: name} from 'name:token,name:token' or 'token,token'."""
    result = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            name, token = entry.split(":", 1)
            result[token.strip()] = name.strip()
        else:
            result[entry] = entry
    return result


def parse_ttl_duration(ttl: str) -> int:
    """Return seconds from a TTL string like '1h', '7d'."""
    if ttl.endswith("h"):
        return int(ttl[:-1]) * 3600
    if ttl.endswith("d"):
        return int(ttl[:-1]) * 86400
    raise ValueError(f"Invalid TTL format: {ttl!r}. Use e.g. '24h' or '7d'.")


class Settings(BaseSettings):
    upload_tokens: str
    allowed_ttls: list[str] = ["1h", "6h", "24h", "48h", "7d"]
    default_ttl: str = "24h"
    max_upload_size: int = 5_242_880
    cleanup_interval_hours: int = 1
    data_dir: str = "./data"
    base_url: str = "http://localhost:52031"

    @property
    def token_map(self) -> dict[str, str]:
        return parse_tokens(self.upload_tokens)


@lru_cache
def get_settings() -> Settings:
    return Settings()
