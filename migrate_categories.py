import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)

conn.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

existing = conn.execute(
    "SELECT COUNT(*) FROM categories WHERE user_id IS NULL"
).fetchone()[0]

if existing == 0:
    defaults = ['Food', 'Transport', 'Shopping', 'Rent', 'Other']
    for name in defaults:
        conn.execute(
            "INSERT INTO categories (user_id, name) VALUES (NULL, ?)",
            (name,)
        )

conn.commit()
conn.close()
print("Migration complete: categories table ready with defaults.")
