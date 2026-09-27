from fastapi import Depends, HTTPException, Header
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import Session as SessionModel, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Falta el token de sesion")

    session = db.get(SessionModel, token)
    if session is None:
        raise HTTPException(status_code=401, detail="Sesion invalida o expirada")

    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return user
