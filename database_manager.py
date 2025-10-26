#!/usr/bin/env python3
"""
Database Management Utility for Wellness App
Handles migration, backup, and maintenance operations
"""

import os
import json
import sqlite3
import shutil
from datetime import datetime, date
from typing import Dict, Any, List
import argparse

# Import our database module
try:
    from database import (
        init_database, create_user_sql, create_user_profile_sql,
        log_health_data_sql, create_session_sql, get_db_connection
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("Database module not available")

# Import existing backend functions
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from backend import (
        load_users_data, load_user_wellness_data, 
        get_all_users, WELLNESS_DATA_DIR, USERS_DATA_FILE
    )
    BACKEND_AVAILABLE = True
except ImportError as e:
    BACKEND_AVAILABLE = False
    print(f"Backend module not available: {e}")
    # Set fallback values
    WELLNESS_DATA_DIR = "wellness_data"
    USERS_DATA_FILE = "users_data.json"
    
    # Fallback functions
    def get_all_users():
        """Fallback function to load users from JSON"""
        if os.path.exists(USERS_DATA_FILE):
            with open(USERS_DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def load_user_wellness_data(user_id):
        """Fallback function to load user wellness data"""
        wellness_file = os.path.join(WELLNESS_DATA_DIR, f"{user_id}_wellness.json")
        if os.path.exists(wellness_file):
            with open(wellness_file, 'r') as f:
                return json.load(f)
        return {}
    
    BACKEND_AVAILABLE = True  # We have fallback functions

def backup_json_data():
    """Backup existing JSON data before migration"""
    # Create Backup directory if it doesn't exist
    main_backup_dir = "Backup"
    os.makedirs(main_backup_dir, exist_ok=True)
    
    backup_dir = os.path.join(main_backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"Creating backup in {backup_dir}/")
    
    # Backup users data
    if os.path.exists(USERS_DATA_FILE):
        shutil.copy2(USERS_DATA_FILE, os.path.join(backup_dir, USERS_DATA_FILE))
        print(f"✓ Backed up {USERS_DATA_FILE}")
    
    # Backup wellness data directory
    if os.path.exists(WELLNESS_DATA_DIR):
        shutil.copytree(WELLNESS_DATA_DIR, os.path.join(backup_dir, WELLNESS_DATA_DIR))
        print(f"✓ Backed up {WELLNESS_DATA_DIR}/")
    
    # Backup ner_data directory if it exists
    if os.path.exists("ner_data"):
        shutil.copytree("ner_data", os.path.join(backup_dir, "ner_data"))
        print(f"✓ Backed up ner_data/")
    
    # Backup existing database if it exists
    if os.path.exists("wellness_app.db"):
        shutil.copy2("wellness_app.db", os.path.join(backup_dir, "wellness_app.db"))
        print(f"✓ Backed up wellness_app.db")
    
    return backup_dir

def migrate_users_to_sql():
    """Migrate user data from JSON to SQL"""
    if not (DATABASE_AVAILABLE and BACKEND_AVAILABLE):
        print("❌ Cannot migrate: Required modules not available")
        return False
    
    print("🔄 Migrating users from JSON to SQL...")
    
    try:
        users_data = get_all_users()
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        print(f"Found {len(users_data)} users in JSON file")
        
        for user_id, user_info in users_data.items():
            try:
                # Handle different JSON structures
                if "full_name" in user_info:
                    # New format (user_0006 style)
                    full_name = user_info.get("full_name", "Unknown User")
                    email = user_info.get("email")
                    phone = user_info.get("phone")
                    cnic = user_info.get("cnic")
                    password_hash = user_info.get("password_hash")
                else:
                    # Old format (user_0001-0005 style)
                    full_name = user_info.get("name", "Unknown User")
                    email = user_info.get("email")
                    phone = user_info.get("phone")
                    cnic = user_info.get("cnic")
                    password_hash = None
                
                # Prepare user data for SQL
                user_sql_data = {
                    "user_id": user_id,
                    "full_name": full_name,
                    "cnic": cnic,
                    "email": email,
                    "phone": phone
                }
                
                # Add password hash if available
                if password_hash:
                    user_sql_data["password_hash"] = password_hash  # Already hashed
                
                print(f"Attempting to migrate: {user_id} ({full_name})")
                result = create_user_sql(user_sql_data)
                
                if result["success"]:
                    migrated_count += 1
                    print(f"✓ Migrated user: {user_id} ({full_name})")
                else:
                    if "already exists" in result["message"]:
                        skipped_count += 1
                        print(f"⚠ Skipped user {user_id}: {result['message']}")
                    else:
                        error_count += 1
                        print(f"❌ Failed to migrate user {user_id}: {result['message']}")
                        
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing user {user_id}: {e}")
        
        print(f"\n📊 Migration Summary:")
        print(f"✓ Migrated: {migrated_count} users")
        print(f"⚠ Skipped: {skipped_count} users (already exist)")
        print(f"❌ Errors: {error_count} users")
        
        return migrated_count > 0 or error_count == 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def migrate_profiles_to_sql():
    """Migrate user profiles from JSON to SQL"""
    if not (DATABASE_AVAILABLE and BACKEND_AVAILABLE):
        print("❌ Cannot migrate profiles: Required modules not available")
        return False
        
    print("🔄 Migrating profiles from JSON to SQL...")
    
    try:
        users_data = get_all_users()
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for user_id, user_info in users_data.items():
            try:
                profile_data = {}
                
                # Check if profile data is embedded in users_data (new format)
                if "age" in user_info or "height" in user_info:
                    # Extract profile from user_info directly
                    profile_data = {
                        "user_id": user_id,
                        "age": user_info.get("age"),
                        "gender": user_info.get("gender"),
                        "height": user_info.get("height"),
                        "current_weight": user_info.get("current_weight"),
                        "target_weight": user_info.get("target_weight"),
                        "initial_weight": user_info.get("initial_weight"),
                        "activity_level": user_info.get("activity_level"),
                        "diet_type": user_info.get("diet_type"),
                        "city": user_info.get("city"),
                        "area": user_info.get("area"),
                        "preferred_language": user_info.get("preferred_language", "English")
                    }
                    
                    # Remove None values
                    profile_data = {k: v for k, v in profile_data.items() if v is not None}
                
                # Also check wellness_data folder for separate profile data
                try:
                    wellness_data = load_user_wellness_data(user_id)
                    wellness_profile = wellness_data.get("profile", {})
                    
                    # Merge wellness profile data (wellness data takes precedence)
                    if wellness_profile:
                        profile_data.update(wellness_profile)
                        profile_data["user_id"] = user_id
                        
                except Exception as e:
                    print(f"⚠ Could not load wellness data for {user_id}: {e}")
                
                if profile_data and len(profile_data) > 1:  # More than just user_id
                    result = create_user_profile_sql(profile_data)
                    
                    if result["success"]:
                        migrated_count += 1
                        print(f"✓ Migrated profile for user: {user_id}")
                    else:
                        error_count += 1
                        print(f"❌ Failed to migrate profile for {user_id}: {result['message']}")
                else:
                    skipped_count += 1
                    print(f"⚠ Skipped {user_id}: No profile data found")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing profile for {user_id}: {e}")
        
        print(f"\n📊 Profile Migration Summary:")
        print(f"✓ Migrated: {migrated_count} profiles")
        print(f"⚠ Skipped: {skipped_count} profiles (no data)")
        print(f"❌ Errors: {error_count} profiles")
        
        return migrated_count > 0 or error_count == 0
        
    except Exception as e:
        print(f"❌ Profile migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def migrate_health_data_to_sql():
    """Migrate health data from JSON to SQL"""
    if not (DATABASE_AVAILABLE and BACKEND_AVAILABLE):
        print("❌ Cannot migrate health data: Required modules not available")
        return False
        
    print("🔄 Migrating health data from JSON to SQL...")
    
    try:
        users_data = get_all_users()
        migrated_count = 0
        
        for user_id in users_data.keys():
            try:
                wellness_data = load_user_wellness_data(user_id)
                health_logs = wellness_data.get("health_logs", {})
                
                for log_date, log_data in health_logs.items():
                    log_data["user_id"] = user_id
                    log_data["date"] = log_date
                    
                    result = log_health_data_sql(log_data)
                    if result["success"]:
                        migrated_count += 1
                    else:
                        print(f"❌ Failed to migrate health data for {user_id} on {log_date}")
                        
            except Exception as e:
                print(f"⚠ Error processing health data for {user_id}: {e}")
        
        print(f"\n📊 Health Data Migration Summary:")
        print(f"✓ Migrated: {migrated_count} health records")
        
        return True
        
    except Exception as e:
        print(f"❌ Health data migration failed: {e}")
        return False

def verify_migration():
    """Verify that migration was successful"""
    if not DATABASE_AVAILABLE:
        print("❌ Cannot verify: Database module not available")
        return False
        
    print("🔍 Verifying migration...")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count users
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Count profiles
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
            profile_count = cursor.fetchone()[0]
            
            # Count health records
            cursor.execute("SELECT COUNT(*) FROM health_data")
            health_count = cursor.fetchone()[0]
            
            # Count sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            
            print(f"\n📊 Database Contents:")
            print(f"👥 Users: {user_count}")
            print(f"📋 Profiles: {profile_count}")
            print(f"🏥 Health Records: {health_count}")
            print(f"💬 Sessions: {session_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def full_migration():
    """Perform complete migration from JSON to SQL"""
    print("🚀 Starting Full Migration Process")
    print("=" * 50)
    
    # Step 1: Initialize database
    if not DATABASE_AVAILABLE:
        print("❌ Database module not available. Cannot proceed.")
        return False
        
    print("1️⃣ Initializing database...")
    try:
        init_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Step 2: Create backup
    print("\n2️⃣ Creating backup...")
    backup_dir = backup_json_data()
    
    # Step 3: Migrate users
    print("\n3️⃣ Migrating users...")
    if not migrate_users_to_sql():
        print("❌ User migration failed")
        return False
    
    # Step 4: Migrate profiles
    print("\n4️⃣ Migrating profiles...")
    if not migrate_profiles_to_sql():
        print("❌ Profile migration failed")
        return False
    
    # Step 5: Migrate health data
    print("\n5️⃣ Migrating health data...")
    if not migrate_health_data_to_sql():
        print("❌ Health data migration failed")
        return False
    
    # Step 6: Verify migration
    print("\n6️⃣ Verifying migration...")
    if not verify_migration():
        print("❌ Migration verification failed")
        return False
    
    print(f"\n🎉 Migration completed successfully!")
    print(f"📁 Backup created in: {backup_dir}")
    print(f"💾 New database: wellness_app.db")
    print("\n⚠️  Important Notes:")
    print("- JSON files are still preserved for conversation data")
    print("- SQL database now handles structured data (users, profiles, health)")
    print("- The app will use hybrid SQL+JSON mode automatically")
    
    return True

def show_database_stats():
    """Show current database statistics"""
    if not DATABASE_AVAILABLE:
        print("❌ Database module not available")
        return
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("📊 Database Statistics")
            print("=" * 30)
            
            # Users
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            active_users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            print(f"👥 Users: {active_users} active / {total_users} total")
            
            # Profiles
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
            profiles = cursor.fetchone()[0]
            print(f"📋 Profiles: {profiles}")
            
            # Health data
            cursor.execute("SELECT COUNT(*) FROM health_data")
            health_records = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM health_data")
            users_with_health = cursor.fetchone()[0]
            print(f"🏥 Health Records: {health_records} ({users_with_health} users)")
            
            # Sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            sessions = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM sessions")
            users_with_sessions = cursor.fetchone()[0]
            print(f"💬 Sessions: {sessions} ({users_with_sessions} users)")
            
            # Routine plans
            cursor.execute("SELECT COUNT(*) FROM routine_plans WHERE is_active = TRUE")
            active_plans = cursor.fetchone()[0]
            print(f"📅 Active Routine Plans: {active_plans}")
            
            # Progress logs
            cursor.execute("SELECT COUNT(*) FROM progress_logs")
            progress_logs = cursor.fetchone()[0]
            print(f"📈 Progress Logs: {progress_logs}")
            
    except Exception as e:
        print(f"❌ Error retrieving stats: {e}")

def main():
    """Main function for command line interface"""
    parser = argparse.ArgumentParser(description="Wellness App Database Manager")
    parser.add_argument("action", choices=[
        "init", "migrate", "verify", "stats", "backup"
    ], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "init":
        print("🔧 Initializing database...")
        if DATABASE_AVAILABLE:
            init_database()
            print("✓ Database initialized successfully")
        else:
            print("❌ Database module not available")
            
    elif args.action == "migrate":
        full_migration()
        
    elif args.action == "verify":
        verify_migration()
        
    elif args.action == "stats":
        show_database_stats()
        
    elif args.action == "backup":
        backup_dir = backup_json_data()
        print(f"✓ Backup created in: {backup_dir}")

if __name__ == "__main__":
    main()