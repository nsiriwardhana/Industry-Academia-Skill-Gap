"""
MySQL Database Initialization Script

This script creates all tables in the MySQL database.
Run this after configuring your .env file with DATABASE_URL.

Usage:
    cd backend
    python scripts/init_mysql_db.py
"""

import sys
from pathlib import Path

# Add src directory to path to import app modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from app.db import engine, Base, DATABASE_URL
from app import models  # This imports all models via __init__.py

def create_tables():
    """Create all tables in the MySQL database"""
    print("=" * 80)
    print("MySQL Database Initialization")
    print("=" * 80)
    
    # Verify DATABASE_URL
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not configured!")
        print("Please create backend/src/.env file with your MySQL connection string.")
        print("Example: DATABASE_URL=mysql+pymysql://root:password@localhost:3306/skillbridge_db")
        sys.exit(1)
    
    print(f"\n📌 Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"   (credentials hidden for security)")
    
    # Test connection
    print("\n🔌 Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure MySQL is running on localhost:3306")
        print("2. Verify database 'skillbridge_db' exists")
        print("3. Check username and password in .env file")
        print("4. Install pymysql: pip install pymysql cryptography")
        sys.exit(1)
    
    # Create all tables
    print("\n📋 Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)
    
    # List created tables
    print("\n📊 Verifying tables in database...")
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"\n✅ Found {len(tables)} tables:")
            for table in sorted(tables):
                print(f"   • {table}")
        else:
            print("⚠️  No tables found (this might indicate an issue)")
    except Exception as e:
        print(f"⚠️  Could not list tables: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Database initialization complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Start the FastAPI server: python -m uvicorn app.main:app --reload")
    print("2. Access the API at: http://localhost:8000")
    print("3. View API docs at: http://localhost:8000/docs")
    print()

if __name__ == "__main__":
    from sqlalchemy import text
    create_tables()