"""
Authentication routes for Supabase Auth integration
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from supabase_client_enhanced import auth
from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/signup")
async def signup(request: SignUpRequest):
    """
    Sign up a new user
    """
    try:
        metadata = {}
        if request.full_name:
            metadata['full_name'] = request.full_name
        if request.company_name:
            metadata['company_name'] = request.company_name
        
        response = auth.sign_up(
            email=request.email,
            password=request.password,
            metadata=metadata
        )
        
        if not response or not response.user:
            raise HTTPException(status_code=400, detail="Sign up failed")
        
        return {
            "message": "Sign up successful. Please check your email for verification.",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "email_confirmed": response.user.email_confirmed_at is not None
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_at": response.session.expires_at if response.session else None
            } if response.session else None
        }
        
    except Exception as e:
        logger.error(f"Sign up error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signin")
async def signin(request: SignInRequest):
    """
    Sign in with email and password
    """
    try:
        response = auth.sign_in(
            email=request.email,
            password=request.password
        )
        
        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "message": "Sign in successful",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at,
                "expires_in": response.session.expires_in
            }
        }
        
    except Exception as e:
        logger.error(f"Sign in error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/signout")
async def signout(current_user = Depends(get_current_user)):
    """
    Sign out current user
    """
    try:
        auth.sign_out()
        return {"message": "Sign out successful"}
    except Exception as e:
        logger.error(f"Sign out error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def refresh(request: RefreshTokenRequest):
    """
    Refresh user session
    """
    try:
        response = auth.refresh_session(request.refresh_token)
        
        if not response or not response.session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        return {
            "message": "Session refreshed",
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at,
                "expires_in": response.session.expires_in
            }
        }
        
    except Exception as e:
        logger.error(f"Refresh session error: {str(e)}")
        raise HTTPException(status_code=401, detail="Failed to refresh session")


@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current user information
    """
    try:
        return {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "email_confirmed": current_user.email_confirmed_at is not None,
                "user_metadata": current_user.user_metadata,
                "created_at": current_user.created_at
            }
        }
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
