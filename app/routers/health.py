from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import Session

from app.database import get_session
from app.settings import get_settings

router = APIRouter()


@router.get("/health")
def health(session: Session = Depends(get_session)):
    checks: dict[str, str] = {}

    try:
        session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    try:
        settings = get_settings()
        probe = Path(settings.data_dir) / "pages" / ".health"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"")
        probe.unlink(missing_ok=True)
        checks["data_dir"] = "ok"
    except Exception as exc:
        checks["data_dir"] = f"error: {exc}"

    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "degraded", **checks},
        status_code=200 if ok else 503,
    )
