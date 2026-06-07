import os
import shutil
from app import app, db
from models import User, Agent, Ticket, Conversation, Message, Sentiment, Emotion, TicketActivity

def recreate_database():
    print("WARNING: This will delete all data in the database!")
    confirm = input("Are you sure you want to recreate the database? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    db_path = 'instance/sentiment_chatbot.db'
    migrations_dir = 'migrations'

    # Drop database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Deleted {db_path}")

    # Optionally clear migrations if you want a clean slate
    # if os.path.exists(migrations_dir):
    #     shutil.rmtree(migrations_dir)
    #     print(f"Deleted {migrations_dir}")

    with app.app_context():
        db.create_all()
        
        from werkzeug.security import generate_password_hash
        # Seed initial data
        admin = User(username="admin", email="admin@sentix.ai", 
                     password_hash=generate_password_hash("admin123", method='scrypt'), 
                     role="admin")
        user = User(username="testuser", email="user@sentix.ai", 
                    password_hash=generate_password_hash("user123", method='scrypt'), 
                    role="user")
        admin_agent = Agent(name="System Admin", email="admin@sentix.ai", role="Lead Support")
        
        db.session.add(admin)
        db.session.add(user)
        db.session.add(admin_agent)
        db.session.commit()
        print("Database recreated and seeded with Admin and Test User.")
        print("Admin: admin@sentix.ai / admin123")
        print("User: user@sentix.ai / user123")

if __name__ == '__main__':
    recreate_database()
