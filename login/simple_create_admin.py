"""Simple script to create admin account using bcrypt directly"""
import sys
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("E:/Integration/login/.env")

# Get database URL from env
DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Create admin table if not exists
db.execute(text("""
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superadmin BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
"""))
db.commit()

# Admin credentials
username = "admin"
email = "admin@example.com"
password = "admin123"  # Change this!

# Check if admin exists
result = db.execute(text("SELECT * FROM admins WHERE username = :username"), {"username": username})
existing = result.fetchone()

if existing:
    print(f"❌ Admin '{username}' already exists!")
else:
    # Hash password using bcrypt directly
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # Insert admin
    db.execute(
        text("""
        INSERT INTO admins (username, email, hashed_password, is_active, is_superadmin)
        VALUES (:username, :email, :password, TRUE, TRUE)
        """),
        {"username": username, "email": email, "password": hashed_password}
    )
    db.commit()
    
    print("✅ Admin account created successfully!")
    print(f"📧 Username: {username}")
    print(f"🔑 Password: {password}")
    print(f"🌐 Email: {email}")
    print(f"⭐ Superadmin: Yes")
    print(f"\n🔐 Login at: http://localhost:3000/admin/login")
    print(f"\n⚠️  IMPORTANT: Change the password after first login!")

db.close()
