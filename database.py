import sqlite3
import hashlib
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import os
from contextlib import contextmanager

# Database file path
DB_FILE = "wellness_app.db"

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable column name access
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize the database with all required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(20) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                cnic VARCHAR(15) UNIQUE,
                email VARCHAR(100),
                password_hash VARCHAR(255),
                phone VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # User profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(20) REFERENCES users(user_id),
                age INTEGER,
                gender TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
                height DECIMAL(5,2),
                current_weight DECIMAL(5,2),
                target_weight DECIMAL(5,2),
                initial_weight DECIMAL(5,2),
                activity_level TEXT CHECK (activity_level IN ('sedentary', 'lightly_active', 'moderately_active', 'very_active')),
                diet_type TEXT CHECK (diet_type IN ('vegetarian', 'non_vegetarian', 'keto', 'low_carb', 'balanced', 'other')),
                city VARCHAR(50),
                area VARCHAR(100),
                preferred_language TEXT CHECK (preferred_language IN ('English', 'Urdu', 'Mixed')) DEFAULT 'English',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Health data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(20) REFERENCES users(user_id),
                date DATE,
                weight DECIMAL(5,2),
                blood_pressure_systolic INTEGER,
                blood_pressure_diastolic INTEGER,
                blood_sugar INTEGER,
                stress_level INTEGER CHECK (stress_level BETWEEN 1 AND 5),
                sleep_hours DECIMAL(3,1),
                mood_rating INTEGER CHECK (mood_rating BETWEEN 1 AND 10),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id VARCHAR(50) UNIQUE NOT NULL,
                user_id VARCHAR(20) REFERENCES users(user_id),
                agent_type TEXT CHECK (agent_type IN ('MENTAL_HEALTH', 'DIET', 'EXERCISE')),
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_messages INTEGER DEFAULT 0,
                session_rating INTEGER CHECK (session_rating BETWEEN 1 AND 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Routine plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routine_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id VARCHAR(50) UNIQUE NOT NULL,
                user_id VARCHAR(20) REFERENCES users(user_id),
                plan_type TEXT CHECK (plan_type IN ('mental_health', 'diet', 'exercise', 'comprehensive')),
                title VARCHAR(200),
                description TEXT,
                start_date DATE,
                end_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Progress logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id VARCHAR(50) REFERENCES routine_plans(plan_id),
                user_id VARCHAR(20) REFERENCES users(user_id),
                log_date DATE,
                completed_activities INTEGER,
                total_activities INTEGER,
                satisfaction_level INTEGER CHECK (satisfaction_level BETWEEN 1 AND 10),
                notes TEXT,
                challenges TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES routine_plans(plan_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Local healthcare table (Pakistan-specific)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS local_healthcare (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200),
                type TEXT CHECK (type IN ('hospital', 'clinic', 'pharmacy', 'lab')),
                city VARCHAR(50),
                area VARCHAR(100),
                address TEXT,
                phone VARCHAR(15),
                emergency_services BOOLEAN DEFAULT FALSE,
                accepts_sehat_card BOOLEAN DEFAULT FALSE,
                specializations TEXT, -- JSON string
                rating DECIMAL(2,1),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("Database initialized successfully!")

# User Management Functions
def create_user_sql(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user in SQL database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Handle password - either hash new password or use existing hash
            password_hash = None
            if user_data.get("password"):
                # Hash new password
                password_hash = hashlib.sha256(user_data["password"].encode()).hexdigest()
            elif user_data.get("password_hash"):
                # Use existing hash (from migration)
                password_hash = user_data["password_hash"]
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (user_id, full_name, cnic, email, password_hash, phone, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data["user_id"],
                user_data["full_name"],
                user_data.get("cnic"),
                user_data.get("email"),
                password_hash,
                user_data.get("phone"),
                datetime.now()
            ))
            
            conn.commit()
            return {"success": True, "message": "User created successfully"}
    
    except sqlite3.IntegrityError as e:
        if "cnic" in str(e).lower():
            return {"success": False, "message": "User with this CNIC already exists"}
        elif "user_id" in str(e).lower():
            return {"success": False, "message": "User ID already exists"}
        else:
            return {"success": False, "message": f"Database error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Error creating user: {str(e)}"}

def get_user_sql(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user information from SQL database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    except Exception as e:
        print(f"Error getting user {user_id}: {e}")
        return None

def update_user_last_active_sql(user_id: str):
    """Update user's last active timestamp"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_active = ? 
                WHERE user_id = ?
            """, (datetime.now(), user_id))
            conn.commit()
    
    except Exception as e:
        print(f"Error updating last active for {user_id}: {e}")

# Profile Management Functions
def create_user_profile_sql(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update user profile in SQL database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if profile exists
            cursor.execute("SELECT id FROM user_profiles WHERE user_id = ?", (profile_data["user_id"],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing profile
                cursor.execute("""
                    UPDATE user_profiles 
                    SET age = ?, gender = ?, height = ?, current_weight = ?, target_weight = ?,
                        initial_weight = ?, activity_level = ?, diet_type = ?, city = ?, area = ?,
                        preferred_language = ?, updated_at = ?
                    WHERE user_id = ?
                """, (
                    profile_data.get("age"),
                    profile_data.get("gender"),
                    profile_data.get("height"),
                    profile_data.get("current_weight"),
                    profile_data.get("target_weight"),
                    profile_data.get("initial_weight"),
                    profile_data.get("activity_level"),
                    profile_data.get("diet_type"),
                    profile_data.get("city"),
                    profile_data.get("area"),
                    profile_data.get("preferred_language", "English"),
                    datetime.now(),
                    profile_data["user_id"]
                ))
                message = "Profile updated successfully"
            else:
                # Create new profile
                cursor.execute("""
                    INSERT INTO user_profiles 
                    (user_id, age, gender, height, current_weight, target_weight, initial_weight,
                     activity_level, diet_type, city, area, preferred_language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile_data["user_id"],
                    profile_data.get("age"),
                    profile_data.get("gender"),
                    profile_data.get("height"),
                    profile_data.get("current_weight"),
                    profile_data.get("target_weight"),
                    profile_data.get("initial_weight"),
                    profile_data.get("activity_level"),
                    profile_data.get("diet_type"),
                    profile_data.get("city"),
                    profile_data.get("area"),
                    profile_data.get("preferred_language", "English")
                ))
                message = "Profile created successfully"
            
            conn.commit()
            return {"success": True, "message": message}
    
    except Exception as e:
        return {"success": False, "message": f"Error managing profile: {str(e)}"}

def get_user_profile_sql(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile from SQL database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    except Exception as e:
        print(f"Error getting profile for {user_id}: {e}")
        return None

# Health Data Functions
def log_health_data_sql(health_data: Dict[str, Any]) -> Dict[str, Any]:
    """Log daily health data"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if data for this date already exists
            cursor.execute("""
                SELECT id FROM health_data 
                WHERE user_id = ? AND date = ?
            """, (health_data["user_id"], health_data["date"]))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE health_data 
                    SET weight = ?, blood_pressure_systolic = ?, blood_pressure_diastolic = ?,
                        blood_sugar = ?, stress_level = ?, sleep_hours = ?, mood_rating = ?, notes = ?
                    WHERE user_id = ? AND date = ?
                """, (
                    health_data.get("weight"),
                    health_data.get("blood_pressure_systolic"),
                    health_data.get("blood_pressure_diastolic"),
                    health_data.get("blood_sugar"),
                    health_data.get("stress_level"),
                    health_data.get("sleep_hours"),
                    health_data.get("mood_rating"),
                    health_data.get("notes"),
                    health_data["user_id"],
                    health_data["date"]
                ))
                message = "Health data updated successfully"
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO health_data 
                    (user_id, date, weight, blood_pressure_systolic, blood_pressure_diastolic,
                     blood_sugar, stress_level, sleep_hours, mood_rating, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health_data["user_id"],
                    health_data["date"],
                    health_data.get("weight"),
                    health_data.get("blood_pressure_systolic"),
                    health_data.get("blood_pressure_diastolic"),
                    health_data.get("blood_sugar"),
                    health_data.get("stress_level"),
                    health_data.get("sleep_hours"),
                    health_data.get("mood_rating"),
                    health_data.get("notes")
                ))
                message = "Health data logged successfully"
            
            conn.commit()
            return {"success": True, "message": message}
    
    except Exception as e:
        return {"success": False, "message": f"Error logging health data: {str(e)}"}

def get_user_health_history_sql(user_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get user's health history for the last N days"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM health_data 
                WHERE user_id = ? 
                ORDER BY date DESC 
                LIMIT ?
            """, (user_id, days))
            
            return [dict(row) for row in cursor.fetchall()]
    
    except Exception as e:
        print(f"Error getting health history for {user_id}: {e}")
        return []

# Session Management Functions
def create_session_sql(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new session record"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sessions 
                (session_id, user_id, agent_type, start_time)
                VALUES (?, ?, ?, ?)
            """, (
                session_data["session_id"],
                session_data["user_id"],
                session_data["agent_type"],
                session_data.get("start_time", datetime.now())
            ))
            
            conn.commit()
            return {"success": True, "message": "Session created successfully"}
    
    except Exception as e:
        return {"success": False, "message": f"Error creating session: {str(e)}"}

def update_session_sql(session_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update session information"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                if key in ["end_time", "total_messages", "session_rating"]:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if set_clauses:
                values.append(session_id)
                cursor.execute(f"""
                    UPDATE sessions 
                    SET {', '.join(set_clauses)}
                    WHERE session_id = ?
                """, values)
                
                conn.commit()
                return {"success": True, "message": "Session updated successfully"}
            else:
                return {"success": False, "message": "No valid fields to update"}
    
    except Exception as e:
        return {"success": False, "message": f"Error updating session: {str(e)}"}

def get_user_sessions_sql(user_id: str, agent_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get user's sessions, optionally filtered by agent type"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if agent_type:
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE user_id = ? AND agent_type = ?
                    ORDER BY created_at DESC
                """, (user_id, agent_type))
            else:
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    except Exception as e:
        print(f"Error getting sessions for {user_id}: {e}")
        return []

# Migration Functions
def migrate_json_to_sql():
    """Migrate existing JSON data to SQL database"""
    print("Starting migration from JSON to SQL...")
    
    # Initialize database first
    init_database()
    
    # Import the existing backend functions
    try:
        from backend import load_users_data, load_user_wellness_data, get_all_users
        
        # Migrate users
        users_data = get_all_users()
        migrated_users = 0
        
        for user_id, user_info in users_data.items():
            user_sql_data = {
                "user_id": user_id,
                "full_name": user_info.get("name", "Unknown"),
                "cnic": user_info.get("cnic"),
                "email": user_info.get("email"),
                "phone": user_info.get("phone")
            }
            
            result = create_user_sql(user_sql_data)
            if result["success"]:
                migrated_users += 1
                
                # Migrate user profile if exists
                try:
                    wellness_data = load_user_wellness_data(user_id)
                    profile = wellness_data.get("profile", {})
                    
                    if profile:
                        profile["user_id"] = user_id
                        create_user_profile_sql(profile)
                        
                except Exception as e:
                    print(f"Error migrating profile for {user_id}: {e}")
        
        print(f"Successfully migrated {migrated_users} users to SQL database")
        
    except ImportError:
        print("Cannot import backend functions. Make sure backend.py is available.")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
    print("Database setup complete!")