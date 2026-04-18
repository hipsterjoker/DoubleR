import sqlite3
from config import DB_PATH
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")

def init_db():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()
    conn.close()

    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()