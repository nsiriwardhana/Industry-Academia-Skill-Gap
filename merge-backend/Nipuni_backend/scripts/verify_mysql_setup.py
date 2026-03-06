"""
MySQL Database Verification Script

Verifies:
1. Database connection
2. Table engines (should be InnoDB)
3. Foreign key constraints
4. Character set configuration

Usage:
    cd backend
    python scripts/verify_mysql_setup.py
"""

import sys
from pathlib import Path
from sqlalchemy import text, inspect

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from app.db import engine, DATABASE_URL


def verify_connection():
    """Test database connection"""
    print("\n" + "=" * 80)
    print("1. DATABASE CONNECTION")
    print("=" * 80)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DATABASE() as db, VERSION() as version"))
            row = result.fetchone()
            print(f"✅ Connected to database: {row[0]}")
            print(f"✅ MySQL version: {row[1]}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def verify_table_engines():
    """Check that all tables use InnoDB engine"""
    print("\n" + "=" * 80)
    print("2. TABLE ENGINES (should be InnoDB)")
    print("=" * 80)
    
    query = text("""
        SELECT table_name, engine, table_collation
        FROM information_schema.tables 
        WHERE table_schema = DATABASE()
        ORDER BY table_name
    """)
    
    non_innodb_tables = []
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
            print(f"\n{'Table Name':<30} {'Engine':<15} {'Collation':<30}")
            print("-" * 80)
            
            for row in rows:
                table_name, engine_type, collation = row
                status = "✅" if engine_type == "InnoDB" else "❌"
                print(f"{status} {table_name:<28} {engine_type:<15} {collation}")
                
                if engine_type != "InnoDB":
                    non_innodb_tables.append(table_name)
            
            if non_innodb_tables:
                print("\n⚠️  WARNING: The following tables are not using InnoDB:")
                for table in non_innodb_tables:
                    print(f"   • {table}")
                    print(f"     Fix: ALTER TABLE {table} ENGINE=InnoDB;")
                return False
            else:
                print("\n✅ All tables are using InnoDB engine")
                return True
                
    except Exception as e:
        print(f"❌ Error checking table engines: {e}")
        return False


def verify_foreign_keys():
    """List all foreign key constraints"""
    print("\n" + "=" * 80)
    print("3. FOREIGN KEY CONSTRAINTS")
    print("=" * 80)
    
    query = text("""
        SELECT 
            constraint_name,
            table_name,
            column_name,
            referenced_table_name,
            referenced_column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = DATABASE()
        AND referenced_table_name IS NOT NULL
        ORDER BY table_name, constraint_name
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
            if rows:
                print(f"\n{'Constraint Name':<35} {'Table':<25} {'Column':<20}")
                print(f"{'References':<35} {'→':<25} {'Referenced':<20}")
                print("-" * 80)
                
                for row in rows:
                    constraint_name, table_name, column_name, ref_table, ref_column = row
                    print(f"✅ {constraint_name:<33}")
                    print(f"   {table_name}.{column_name} → {ref_table}.{ref_column}")
                    print()
                
                print(f"✅ Found {len(rows)} foreign key constraint(s)")
            else:
                print("\n⚠️  No foreign key constraints found")
                print("   This is OK if using SQLAlchemy relationships without explicit FKs")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking foreign keys: {e}")
        return False


def verify_charset():
    """Verify database and table character sets"""
    print("\n" + "=" * 80)
    print("4. CHARACTER SET CONFIGURATION")
    print("=" * 80)
    
    db_query = text("""
        SELECT 
            DEFAULT_CHARACTER_SET_NAME as charset,
            DEFAULT_COLLATION_NAME as collation
        FROM information_schema.SCHEMATA 
        WHERE SCHEMA_NAME = DATABASE()
    """)
    
    try:
        with engine.connect() as conn:
            # Database charset
            result = conn.execute(db_query)
            row = result.fetchone()
            print(f"\nDatabase Character Set: {row[0]}")
            print(f"Database Collation: {row[1]}")
            
            if 'utf8' in row[0].lower():
                print("✅ Database uses UTF-8 encoding")
            else:
                print("⚠️  Database is not using UTF-8")
            
            # Connection charset
            result = conn.execute(text("SHOW VARIABLES LIKE 'character_set_connection'"))
            row = result.fetchone()
            print(f"\nConnection Character Set: {row[1]}")
            
            if 'utf8' in row[1].lower():
                print("✅ Connection uses UTF-8 encoding")
            else:
                print("⚠️  Connection is not using UTF-8")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking character set: {e}")
        return False


def verify_indexes():
    """List indexes on tables"""
    print("\n" + "=" * 80)
    print("5. TABLE INDEXES")
    print("=" * 80)
    
    query = text("""
        SELECT 
            table_name,
            index_name,
            GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
            non_unique
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
        GROUP BY table_name, index_name, non_unique
        ORDER BY table_name, index_name
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
            current_table = None
            index_count = 0
            
            for row in rows:
                table_name, index_name, columns, non_unique = row
                
                if current_table != table_name:
                    if current_table is not None:
                        print()
                    print(f"\n📊 {table_name}")
                    print("-" * 80)
                    current_table = table_name
                
                index_type = "INDEX" if non_unique else "UNIQUE"
                if index_name == "PRIMARY":
                    index_type = "PRIMARY KEY"
                
                print(f"   • {index_type:<12} {index_name:<30} ({columns})")
                index_count += 1
            
            print(f"\n✅ Found {index_count} index(es) across all tables")
            return True
            
    except Exception as e:
        print(f"❌ Error checking indexes: {e}")
        return False


def main():
    """Run all verification checks"""
    print("=" * 80)
    print("MySQL Database Verification")
    print("=" * 80)
    print(f"\nDatabase URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    all_passed = True
    
    # Run all checks
    all_passed &= verify_connection()
    all_passed &= verify_table_engines()
    all_passed &= verify_foreign_keys()
    all_passed &= verify_charset()
    all_passed &= verify_indexes()
    
    # Final summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED")
    else:
        print("⚠️  SOME VERIFICATIONS FAILED - See details above")
    print("=" * 80)
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
