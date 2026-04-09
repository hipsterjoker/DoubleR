import sqlite3

def init_db():
    with open("db/schema.sql", "r", encoding="utf-8") as f:
        schema = f.read()

    conn = sqlite3.connect("database.db")
    conn.executescript(schema)
    conn.commit()
    conn.close()

    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()