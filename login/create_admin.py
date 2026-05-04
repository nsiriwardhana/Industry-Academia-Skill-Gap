"""
Script to create initial admin account
Run this once to create your first admin user
"""
import os
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models import Admin, Base

def create_initial_admin():
    """Create the first admin account"""
    
    # Create tables if they don't exist
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created/verified")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if any admin exists
        existing_admin = db.query(Admin).first()
        
        if existing_admin:
            print("❌ Admin account already exists!")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            print("\nUse the admin login to access the dashboard.")
            return
        
        # Get admin details from user
        print("\n" + "="*50)
        print("CREATE INITIAL ADMIN ACCOUNT")
        print("="*50)
        
        username = input("Enter admin username: ").strip()
        if not username:
            print("❌ Username cannot be empty!")
            return
        
        email = input("Enter admin email: ").strip()
        if not email:
            print("❌ Email cannot be empty!")
            return
        
        full_name = input("Enter admin full name (optional): ").strip()
        
        password = input("Enter admin password: ").strip()
        if not password:
            print("❌ Password cannot be empty!")
            return
        
        confirm_password = input("Confirm password: ").strip()
        if password != confirm_password:
            print("❌ Passwords do not match!")
            return
        
        # Create admin account
        new_admin = Admin(
            username=username,
            email=email,
            full_name=full_name if full_name else None,
            hashed_password=Admin.hash_password(password),
            is_superadmin=True  # First admin is always superadmin
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print("\n" + "="*50)
        print("✅ ADMIN ACCOUNT CREATED SUCCESSFULLY!")
        print("="*50)
        print(f"Username: {new_admin.username}")
        print(f"Email: {new_admin.email}")
        print(f"Full Name: {new_admin.full_name or 'Not provided'}")
        print(f"Role: Superadmin")
        print("\nYou can now login at: http://localhost:3000/admin/login")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_admin()
