from flask import Flask, render_template
from routes.auth_routes import auth_bp
from routes.group_routes import group_bp
from routes.expense_routes import expense_bp
from routes.personal_plan_routes import personal_plan_bp
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(group_bp)
app.register_blueprint(expense_bp)
app.register_blueprint(personal_plan_bp)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)