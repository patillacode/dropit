from sqlmodel import Session

from app.auth import generate_token, hash_token
from app.models import User


def regenerate_token(user: User, session: Session) -> str:
    token = generate_token()
    user.token_hash = hash_token(token)
    session.add(user)
    session.commit()
    return token
