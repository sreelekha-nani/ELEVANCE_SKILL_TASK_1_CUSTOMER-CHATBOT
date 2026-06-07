import sqlite3
import os
from app import app, db
from models import User

def migrate_schema():
    db_path = 'instance/sentiment_chatbot.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Check if role column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'role' not in columns:
        print("Adding 'role' column to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
            conn.commit()
            print("Successfully added 'role' column.")
        except Exception as e:
            print(f"Error adding column: {e}")
            conn.close()
            return
    else:
        print("'role' column already exists.")

    conn.close()

    # 2. Update specific users using SQLAlchemy
    with app.app_context():
        print("Updating specific user roles...")
        
        # bayamsreelekha99@gmail.com -> role='user'
        user1 = User.query.filter_by(email='bayamsreelekha99@gmail.com').first()
        if user1:
            user1.role = 'user'
            print(f"Set role='user' for {user1.email}")
        
        # nani123@gmail.com -> role='admin'
        admin1 = User.query.filter_by(email='nani123@gmail.com').first()
        if admin1:
            admin1.role = 'admin'
            print(f"Set role='admin' for {admin1.email}")
            
        # Ensure everyone else has a role
        User.query.filter(User.role.is_(None)).update({"role": "user"})
        
        try:
            db.session.commit()
            print("Successfully updated user records.")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating records: {e}")

if __name__ == '__main__':
    migrate_schema()
