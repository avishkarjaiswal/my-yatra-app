"""
Database migration script to recreate the database with new schema.
Run this after stopping the Flask server.
"""
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def recreate_database():
    """Drop and recreate all database tables"""
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables with new schema...")
        db.create_all()
        print("✅ Database recreated successfully!")
        print("You can now restart the Flask server.")

if __name__ == '__main__':
    recreate_database()
