#!/usr/bin/env python3
"""Create initial admin user directly in database"""
import sqlite3
import sys
from werkzeug.security import generate_password_hash

def create_admin(email, password, name="Administrator"):
    db_path = "database/harmony_installer.db"
    
    # Validate password
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Check if any users exist
        cursor = conn.execute("SELECT COUNT(*) as count FROM users")
        if cursor.fetchone()["count"] > 0:
            print("Error: Users already exist. Cannot run setup.")
            return False
        
        # Create admin user
        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            """INSERT INTO users (email, password_hash, name, role, company_id, is_active)
               VALUES (?, ?, ?, 'admin', NULL, 1)""",
            (email.lower(), password_hash, name)
        )
        user_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Admin user created successfully!")
        print(f"   ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Name: {name}")
        print(f"   Role: admin")
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [name]")
        print("Example: python create_admin.py admin@example.com mypassword123 Administrator")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Administrator"
    
    create_admin(email, password, name)
