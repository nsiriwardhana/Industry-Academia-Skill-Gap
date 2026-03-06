"""
Admin authentication and dashboard routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from app.database import get_db
from app.models import Admin, User, Candidate, ProcessingStatus
from app.auth_utils import create_access_token, get_current_admin
from app.config import settings

# Create router
router = APIRouter(prefix="/admin", tags=["Admin"])


# ============= Pydantic Schemas =============

class AdminLoginRequest(BaseModel):
    """Schema for admin login request"""
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    """Schema for admin login response"""
    access_token: str
    token_type: str = "bearer"
    admin: dict


class AdminCreateRequest(BaseModel):
    """Schema for creating a new admin"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_superadmin: bool = False


class AdminUpdateRequest(BaseModel):
    """Schema for updating admin details"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class DashboardStats(BaseModel):
    """Schema for dashboard statistics"""
    total_users: int
    total_candidates: int
    active_analyses: int
    pending_processing: int
    recent_registrations: int


# ============= Admin Authentication Routes =============

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    credentials: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin login with username and password.
    
    Returns JWT token with admin privileges for accessing admin-only endpoints.
    
    Example:
        POST /admin/login
        {
            "username": "admin",
            "password": "securepassword"
        }
    """
    # Find admin by username
    admin = db.query(Admin).filter(Admin.username == credentials.username).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not admin.verify_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if admin account is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    # Update last login timestamp
    admin.last_login = datetime.utcnow()
    db.commit()
    
    # Create JWT token with admin flag
    access_token = create_access_token(
        data={
            "admin_id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "is_admin": True,
            "is_superadmin": admin.is_superadmin
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": admin.to_dict()
    }


@router.get("/me")
async def get_current_admin_info(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get current admin's information.
    
    Protected route - requires valid admin JWT token.
    """
    return {
        "success": True,
        "admin": current_admin.to_dict()
    }


# ============= Dashboard Statistics Routes =============

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for admin overview.
    
    Returns:
        - Total users count
        - Total candidates count
        - Active analyses count
        - Pending processing count
        - Recent registrations (last 7 days)
    """
    # Total users
    total_users = db.query(func.count(User.id)).scalar()
    
    # Total candidates
    total_candidates = db.query(func.count(Candidate.id)).scalar()
    
    # Active analyses (candidates with recent analysis)
    from datetime import timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_analyses = db.query(func.count(Candidate.id)).filter(
        Candidate.latest_analysis_date >= seven_days_ago
    ).scalar()
    
    # Pending processing
    pending_processing = db.query(func.count(Candidate.id)).filter(
        Candidate.status == ProcessingStatus.PENDING
    ).scalar()
    
    # Recent registrations
    recent_registrations = db.query(func.count(User.id)).filter(
        User.created_at >= seven_days_ago
    ).scalar()
    
    return {
        "total_users": total_users or 0,
        "total_candidates": total_candidates or 0,
        "active_analyses": active_analyses or 0,
        "pending_processing": pending_processing or 0,
        "recent_registrations": recent_registrations or 0
    }


# ============= User Management Routes =============

@router.get("/users")
async def get_all_users(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None
):
    """
    Get all users with pagination and search.
    
    Query Parameters:
        - skip: Number of records to skip (pagination)
        - limit: Maximum number of records to return
        - search: Search by email or name
    """
    query = db.query(User)
    
    # Apply search filter
    if search:
        query = query.filter(
            (User.email.contains(search)) | (User.name.contains(search))
        )
    
    # Get total count
    total = query.count()
    
    # Get paginated users
    users = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": [user.to_dict() for user in users]
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get candidate profile if exists
    candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()
    
    user_data = user.to_dict()
    if candidate:
        user_data["candidate"] = {
            "id": candidate.id,
            "target_role": candidate.target_role.value if candidate.target_role else None,
            "status": candidate.status.value if candidate.status else None,
            "readiness_score": candidate.readiness_score,
            "latest_analysis_date": candidate.latest_analysis_date.isoformat() if candidate.latest_analysis_date else None,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None
        }
    
    return {
        "success": True,
        "user": user_data
    }


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active_status(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle user's active status (activate/deactivate account).
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Toggle active status
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": f"User account {'activated' if user.is_active else 'deactivated'}",
        "user": user.to_dict()
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user account (only for superadmin).
    
    This will also delete all associated candidate profiles and documents
    due to CASCADE delete constraint.
    """
    # Check if current admin is superadmin
    if not current_admin.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can delete users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "message": "User deleted successfully"
    }


# ============= Admin Management Routes (Superadmin Only) =============

@router.post("/admins", status_code=status.HTTP_201_CREATED)
async def create_admin(
    admin_data: AdminCreateRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new admin account (superadmin only).
    """
    # Check if current admin is superadmin
    if not current_admin.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create admin accounts"
        )
    
    # Check if username already exists
    existing_username = db.query(Admin).filter(Admin.username == admin_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create new admin
    new_admin = Admin(
        username=admin_data.username,
        email=admin_data.email,
        hashed_password=Admin.hash_password(admin_data.password),
        full_name=admin_data.full_name,
        is_superadmin=admin_data.is_superadmin
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return {
        "success": True,
        "message": "Admin created successfully",
        "admin": new_admin.to_dict()
    }


@router.get("/admins")
async def get_all_admins(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all admin accounts (superadmin only).
    """
    # Check if current admin is superadmin
    if not current_admin.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can view all admins"
        )
    
    admins = db.query(Admin).all()
    
    return {
        "success": True,
        "admins": [admin.to_dict() for admin in admins]
    }
