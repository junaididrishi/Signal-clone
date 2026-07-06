from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

MOCK_OTP = "123456"


@router.post("/register", response_model=schemas.Token)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if user_data.otp != MOCK_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP. Use 123456 for testing.")

    if db.query(models.User).filter(models.User.phone == user_data.phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = models.User(
        phone=user_data.phone,
        username=user_data.username,
        display_name=user_data.display_name,
        hashed_password=get_password_hash(user_data.password),
        avatar_url=f"https://api.dicebear.com/7.x/thumbs/svg?seed={user_data.username}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.phone == credentials.phone).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid phone number or password")

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=schemas.UserOut)
def update_profile(
    update_data: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if update_data.display_name is not None:
        current_user.display_name = update_data.display_name
    if update_data.about is not None:
        current_user.about = update_data.about
    if update_data.avatar_url is not None:
        current_user.avatar_url = update_data.avatar_url
    db.commit()
    db.refresh(current_user)
    return current_user
