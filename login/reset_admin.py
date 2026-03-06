"""
Script to reset admin account with correct bcrypt hash
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Admin, Base
import bcrypt

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Delete existing admin
    db.query(Admin).filter(Admin.username == "admin").delete()
    db.commit()
    print("✅ Deleted old admin account")
    
    # Create new admin with correct bcrypt hash
    password = "admin123"  # Simple password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    new_admin = Admin(
        username="admin",
        email="admin@skillscope.com",
        full_name="System Administrator",
        hashed_password=hashed.decode('utf-8'),
        is_superadmin=True,
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    print("\n" + "="*50)
    print("✅ ADMIN ACCOUNT CREATED SUCCESSFULLY!")
    print("="*50)
    print(f"Username: admin")
    print(f"Password: admin123")
    print(f"Email: admin@skillscope.com")
    print(f"Role: Superadmin")
    print("\nLogin at: http://localhost:8081/admin/login")
    print("="*50)
    
except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
