-- ========================================
-- MySQL User Setup for SkillBridge
-- ========================================
-- This script creates a dedicated database user for the application
-- Run this as MySQL root user

-- 1. Create dedicated user
CREATE USER IF NOT EXISTS 'skillbridge_user'@'localhost' IDENTIFIED BY 'skillbridge_secure_2026';

-- 2. Grant all privileges on skillbridge_db
GRANT ALL PRIVILEGES ON skillbridge_db.* TO 'skillbridge_user'@'localhost';

-- 3. Apply changes
FLUSH PRIVILEGES;

-- 4. Verify user was created
SELECT User, Host FROM mysql.user WHERE User = 'skillbridge_user';

-- 5. Show granted privileges
SHOW GRANTS FOR 'skillbridge_user'@'localhost';

-- ========================================
-- How to run this script:
-- ========================================
-- Method 1: MySQL CLI
--   mysql -u root -p < scripts/setup_mysql_user.sql
--
-- Method 2: MySQL Workbench
--   Open this file and execute
--
-- Method 3: Command line
--   mysql -u root -p -e "source scripts/setup_mysql_user.sql"
--
-- ========================================
-- After running:
-- ========================================
-- Update your .env file:
--   DATABASE_URL=mysql+pymysql://skillbridge_user:skillbridge_secure_2026@localhost:3306/skillbridge_db?charset=utf8mb4
--
-- IMPORTANT: Change the password 'skillbridge_secure_2026' to something secure!
-- ========================================
