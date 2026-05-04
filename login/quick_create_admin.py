"""Quick script to create an admin account"""
import sys
sys.path.insert(0, "E:/Integration/login")

from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("E:/Integration/login/.env")

# Create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Get database URL from env or construct it
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "oauth_users")
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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
    # Hash password
    hashed_password = pwd_context.hash(password)
    
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
