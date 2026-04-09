from flask import Flask, render_template
from init_db import init_db
from routes.auth_routes import auth_bp
from routes.group_routes import group_bp
from routes.expense_routes import expense_bp

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

app.register_blueprint(auth_bp)
app.register_blueprint(group_bp)
app.register_blueprint(expense_bp)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)