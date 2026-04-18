import os
import sqlite3
from flask import g, current_app

DATABASE_NAME = 'edutrack.db'

def get_db():
    if 'db' not in g:
        db_path = os.path.join(current_app.instance_path, DATABASE_NAME)
        os.makedirs(current_app.instance_path, exist_ok=True)
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON;')
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
    with open(schema_path, 'rb') as f:
        db.executescript(f.read().decode('utf8'))
    seed_classes(db)
    db.commit()

def seed_classes(db):
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
