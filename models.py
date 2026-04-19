import os
import sqlite3
from flask import g, current_app

DATABASE_NAME = 'edutrack.db'

def get_db():
    if 'db' not in g:
        try:
            db_path = os.path.join(current_app.instance_path, DATABASE_NAME)
            os.makedirs(current_app.instance_path, exist_ok=True)
            g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys = ON;')
            print(f"Database connected: {db_path}")
        except Exception as e:
            print(f"ERROR connecting to database: {e}")
            raise
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    db = get_db()
    cursor = db.execute(query, args)
    rv = cursor.fetchall()
    cursor.close()
    return (rv[0] if rv else None) if one else rv

def init_db():
    db = get_db()
    schema_path = os.path.join(current_app.root_path, 'schema.sql')
    try:
        # Check if tables already exist to avoid re-initialization
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            return  # Tables already exist, skip initialization
        
        # Initialize schema if tables don't exist
        if not os.path.exists(schema_path):
            print(f"ERROR: schema.sql not found at {schema_path}")
            return
        
        with open(schema_path, 'rb') as f:
            db.executescript(f.read().decode('utf8'))
        seed_classes(db)
        db.commit()
    except Exception as e:
        print(f"ERROR initializing database: {e}")
        db.rollback()

def seed_classes(db):
    try:
        default_classes = [
            'Computer Science',
            'Mathematics',
            'Physics',
            'Chemistry',
            'Biology',
            'English'
        ]
        for class_name in default_classes:
            db.execute('INSERT OR IGNORE INTO classes (name) VALUES (?)', (class_name,))
    except Exception as e:
        print(f"ERROR seeding classes: {e}")
