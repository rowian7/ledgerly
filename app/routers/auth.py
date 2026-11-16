from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.username == body.username.lower()))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    user = User(username=body.username.lower(), hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    return user


@router.post("/login", response_model=Token)
def login(body: UserCreate, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username.lower()))
    # Same error for "no such user" and "wrong password" so usernames can't be probed.
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
