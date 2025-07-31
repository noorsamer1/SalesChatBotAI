# app/routes/auth_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.core.db import get_db
from app.models.auth import User
from app.services.auth_utils import hash_password, verify_password, create_access_token
from backend.app.services.auth_deps import get_current_user

router = APIRouter()

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
    (User.username == user.username) | (User.email == user.email)
).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"msg": "Registration successful!"}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token({"sub": str(db_user.id), "username": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ✅ NEW: Logout endpoint
@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint - Since you're using stateless JWT tokens,
    this endpoint mainly serves to validate the token and return success.
    The actual logout is handled by the frontend removing the token.
    """
    return {
        "message": "Successfully logged out", 
        "user": current_user.username
    }

# ✅ NEW: Get current user info
@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

# ✅ NEW: Refresh token endpoint
@router.post("/refresh")
def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh the access token (useful for extending session)
    """
    access_token = create_access_token({
        "sub": str(current_user.id), 
        "username": current_user.username
    })
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }