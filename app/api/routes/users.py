from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession):
    existing = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=list[UserRead])
def list_users(db: DbSession, skip: int = 0, limit: int = 50):
    return db.scalars(select(User).offset(skip).limit(limit)).all()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user