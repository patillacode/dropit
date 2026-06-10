from fastapi import HTTPException, status


def clean_required_name(raw: str, *, lower: bool = False) -> str:
    name = raw.strip()
    if lower:
        name = name.lower()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Name required"
        )
    return name
