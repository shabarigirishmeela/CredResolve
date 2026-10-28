import secrets
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user_payload, get_password_hash
from app.models.schema import User
from app.schemas.dtos import LoginRequest, Token, UserResponse, GoogleTokenRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(creds: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == creds.email).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please verify your credentials."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact your system administrator."
        )

    token = create_access_token(subject=user.email, role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.post("/google", response_model=Token)
def google_login(creds: GoogleTokenRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured on this server. Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the backend environment."
        )

    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={creds.id_token}")
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Google OAuth token."
                )
            info = resp.json()
            aud = info.get("aud")
            if aud != settings.GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token client ID mismatch."
                )
            email = info.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in Google OAuth token payload."
                )
            name = info.get("name", email.split("@")[0])
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=get_password_hash(secrets.token_hex(24)),
                    full_name=name,
                    role=settings.GOOGLE_DEFAULT_ROLE,
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            elif not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive. Please contact system administrator."
                )

            token = create_access_token(subject=user.email, role=user.role)
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )

@router.get("/me")
def get_current_user(payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    }

@router.get("/demo-users")
def get_demo_users():
    return [
        {
            "email": "admin@credresolve.com",
            "password": "credresolve123",
            "full_name": "Rajesh Sharma",
            "role": "admin",
            "description": "Full administrative control, configuration, audit and user management"
        },
        {
            "email": "manager@credresolve.com",
            "password": "credresolve123",
            "full_name": "Priya Nair",
            "role": "manager",
            "description": "Operations head, campaign analytics, agent performance oversight"
        },
        {
            "email": "agent@credresolve.com",
            "password": "credresolve123",
            "full_name": "Anil Verma",
            "role": "agent",
            "description": "Senior recovery agent, active queue, borrower contact logs"
        },
        {
            "email": "auditor@credresolve.com",
            "password": "credresolve123",
            "full_name": "Kavita Rao",
            "role": "auditor",
            "description": "Compliance & grievance auditor, Fair Practices Code tracking"
        }
    ]
