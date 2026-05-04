"""
Migration: Add new TargetRole enum values to candidates table.
The DB stores Python enum names (ML_ENGINEER), not values (ML Engineer).
"""
import os, re, sys
from dotenv import load_dotenv
import pymysql

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/oauth_users")

match = re.match(r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)", DATABASE_URL)
if not match:
    raise ValueError(f"Cannot parse DATABASE_URL: {DATABASE_URL}")

user, password, host, port, database = match.groups()
port = int(port) if port else 3306

conn = pymysql.connect(host=host, user=user, password=password, database=database, port=port)
cursor = conn.cursor()

print("Checking current ENUM values for target_role column...")
cursor.execute(
    "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'candidates' AND COLUMN_NAME = 'target_role'",
    (database,)
)
row = cursor.fetchone()
if row:
    print(f"   Current: {row[0]}")
else:
    print("   WARNING: Column not found!")
    conn.close()
    sys.exit(1)

# MySQL stores enum names (Python keys), not values
print("Updating ENUM to include AI_ML_ENGINEER and WEB_DEVELOPER keys...")
cursor.execute("""
    ALTER TABLE candidates 
    MODIFY COLUMN target_role 
    ENUM(
        'AI_ML_ENGINEER',
        'ML_ENGINEER',
        'DATA_ANALYST',
        'DATA_ENGINEER',
        'DATA_SCIENTIST',
        'SOFTWARE_ENGINEER',
        'DEVOPS_ENGINEER',
        'WEB_DEVELOPER'
    ) NOT NULL
""")
conn.commit()
print("ENUM updated successfully!")

cursor.execute(
    "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'candidates' AND COLUMN_NAME = 'target_role'",
    (database,)
)
row = cursor.fetchone()
print(f"New enum: {row[0]}")
conn.close()
print("Migration complete!")
