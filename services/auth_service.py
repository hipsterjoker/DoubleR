from db.connection import get_db_connection

def register_user(username, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    # check if user exists
    existing_user = cursor.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()

    if existing_user:
        conn.close()
        return False, "Username or email already exists."

    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (username, email, password)
    )
    conn.commit()
    conn.close()

    return True, "Registration successful."

def login_user(username, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()
    conn.close()

    if user:
        return True, user
    return False, "Invalid username or password."