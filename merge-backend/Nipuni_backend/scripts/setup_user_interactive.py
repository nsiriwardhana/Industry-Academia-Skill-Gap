"""
MySQL User Setup Helper Script

This script helps create the dedicated MySQL user for SkillBridge.
It provides interactive prompts and generates the SQL commands.

Usage:
    cd backend
    python scripts/setup_user_interactive.py
"""

import getpass
import secrets
import string


def generate_secure_password(length=20):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


def create_user_sql(username, password):
    """Generate SQL commands to create user and grant privileges"""
    return f"""
-- ========================================
-- SkillBridge MySQL User Setup
-- ========================================

-- 1. Create user
CREATE USER IF NOT EXISTS '{username}'@'localhost' IDENTIFIED BY '{password}';

-- 2. Grant privileges
GRANT ALL PRIVILEGES ON skillbridge_db.* TO '{username}'@'localhost';

-- 3. Apply changes
FLUSH PRIVILEGES;

-- 4. Verify (optional - run these manually to check)
-- SELECT User, Host FROM mysql.user WHERE User = '{username}';
-- SHOW GRANTS FOR '{username}'@'localhost';
"""


def create_env_config(username, password):
    """Generate .env file content"""
    return f"""# MySQL Database Configuration
DATABASE_URL=mysql+pymysql://{username}:{password}@localhost:3306/skillbridge_db?charset=utf8mb4
"""


def main():
    print("=" * 80)
    print("SkillBridge - MySQL User Setup Helper")
    print("=" * 80)
    print("\nThis script will help you create a dedicated MySQL user for the application.")
    print("You'll need MySQL root access to create the user.\n")
    
    # Get username
    print("Step 1: Choose MySQL username")
    print("-" * 80)
    username = input("Enter username (default: skillbridge_user): ").strip()
    if not username:
        username = "skillbridge_user"
    print(f"✓ Using username: {username}")
    
    # Get password
    print("\nStep 2: Choose password")
    print("-" * 80)
    print("Options:")
    print("  1. Generate secure random password (recommended)")
    print("  2. Enter your own password")
    
    choice = input("\nChoice (1 or 2): ").strip()
    
    if choice == "1":
        password = generate_secure_password()
        print(f"✓ Generated secure password: {password}")
        print("  (Make sure to save this!)")
    else:
        password = getpass.getpass("Enter password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("❌ Passwords don't match. Exiting.")
            return 1
        
        if len(password) < 8:
            print("⚠️  Warning: Password is short. Consider using a longer password.")
        
        print("✓ Password set")
    
    # Generate files
    print("\n" + "=" * 80)
    print("GENERATED FILES")
    print("=" * 80)
    
    # Save SQL file
    sql_filename = "setup_mysql_user_generated.sql"
    with open(sql_filename, "w") as f:
        f.write(create_user_sql(username, password))
    print(f"\n✅ SQL script saved: {sql_filename}")
    
    # Save .env template
    env_filename = ".env.generated"
    with open(env_filename, "w") as f:
        f.write(create_env_config(username, password))
    print(f"✅ .env config saved: {env_filename}")
    
    # Instructions
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    
    print(f"""
1. Create the MySQL user by running the SQL script:
   
   mysql -u root -p < {sql_filename}
   
   Or manually in MySQL:
   - Open MySQL Workbench or CLI as root
   - Execute the contents of {sql_filename}

2. Update your .env file:
   
   cd src
   cp ../{env_filename} .env
   
   Or manually copy the DATABASE_URL from {env_filename}

3. Test the connection:
   
   cd backend
   python scripts/verify_mysql_setup.py

4. Run migrations:
   
   cd backend/src
   alembic upgrade head

5. Start the application:
   
   cd backend/src
   python -m uvicorn app.main:app --reload

""")
    
    print("=" * 80)
    print("✅ Setup files generated successfully!")
    print("=" * 80)
    print()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
