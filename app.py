from flask import Flask, render_template, session
from datetime import datetime, timedelta
import time as _time
from routes.auth_routes import auth_bp
from routes.group_routes import group_bp
from routes.expense_routes import expense_bp
from routes.personal_plan_routes import personal_plan_bp
from routes.notification_routes import notification_bp
from routes.category_routes import category_bp
from config import SECRET_KEY
from db.connection import get_db_connection

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(group_bp)
app.register_blueprint(expense_bp)
app.register_blueprint(personal_plan_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(category_bp)


@app.template_filter("localtime")
def localtime_filter(value):
    """Convert a UTC datetime string from SQLite to local system time."""
    if not value:
        return value
    try:
        dt = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        # Read the system's UTC offset dynamically (works for any timezone)
        offset_seconds = -_time.timezone if not _time.daylight else -_time.altzone
        dt = dt + timedelta(seconds=offset_seconds)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


@app.context_processor
def inject_notification_count():
    """Inject pending notification count into every template."""
    count = 0
    if "user_id" in session:
        try:
            conn = get_db_connection()
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM invitations i
                JOIN groups g ON g.id = i.group_id
                JOIN users u ON u.id = i.sender_id
                WHERE i.receiver_id = ? AND i.status = 'pending'
                """,
                (session["user_id"],)
            ).fetchone()
            conn.close()
            count = row["cnt"] if row else 0
        except Exception:
            count = 0
    return {"notification_count": count}


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)