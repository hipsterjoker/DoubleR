from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.connection import get_db_connection

personal_plan_bp = Blueprint("personal_plan", __name__)


@personal_plan_bp.route("/personal-plans")
def list_personal_plans():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    plans = conn.execute("""
        SELECT 
            p.id,
            p.title,
            p.description,
            p.created_at,
            COALESCE(SUM(e.amount), 0) AS total
        FROM personal_plans p
        LEFT JOIN personal_plan_expenses e ON p.id = e.plan_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """, (user_id,)).fetchall()

    conn.close()
    return render_template("personal_plans/list.html", plans=plans)


@personal_plan_bp.route("/personal-plans/create", methods=["GET", "POST"])
def create_personal_plan():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description", "").strip()
        user_id = session["user_id"]

        if not title.strip():
            flash("Plan title is required.", "danger")
            return redirect(url_for("personal_plan.create_personal_plan"))

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO personal_plans (user_id, title, description)
            VALUES (?, ?, ?)
        """, (user_id, title.strip(), description))
        conn.commit()
        conn.close()

        flash("Personal plan created successfully!", "success")
        return redirect(url_for("personal_plan.list_personal_plans"))

    return render_template("personal_plans/create.html")


@personal_plan_bp.route("/personal-plans/<int:plan_id>")
def personal_plan_detail(plan_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    plan = conn.execute("""
        SELECT *
        FROM personal_plans
        WHERE id = ? AND user_id = ?
    """, (plan_id, user_id)).fetchone()

    if plan is None:
        conn.close()
        flash("Plan not found.", "danger")
        return redirect(url_for("personal_plan.list_personal_plans"))

    expenses = conn.execute("""
        SELECT *
        FROM personal_plan_expenses
        WHERE plan_id = ? AND user_id = ?
        ORDER BY created_at DESC
    """, (plan_id, user_id)).fetchall()

    total_row = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM personal_plan_expenses
        WHERE plan_id = ? AND user_id = ?
    """, (plan_id, user_id)).fetchone()

    total = total_row["total"] if total_row else 0

    conn.close()
    return render_template(
        "personal_plans/detail.html",
        plan=plan,
        expenses=expenses,
        total=total
    )


@personal_plan_bp.route("/personal-plans/<int:plan_id>/add-expense", methods=["GET", "POST"])
def add_personal_plan_expense(plan_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    plan = conn.execute("""
        SELECT *
        FROM personal_plans
        WHERE id = ? AND user_id = ?
    """, (plan_id, user_id)).fetchone()

    if plan is None:
        conn.close()
        flash("Plan not found.", "danger")
        return redirect(url_for("personal_plan.list_personal_plans"))

    if request.method == "POST":
        title = request.form["title"].strip()
        amount = request.form["amount"]
        category = request.form.get("category", "").strip()
        note = request.form.get("note", "").strip()

        if not title or not amount:
            conn.close()
            flash("Title and amount are required.", "danger")
            return redirect(url_for("personal_plan.add_personal_plan_expense", plan_id=plan_id))

        try:
            amount = float(amount)
        except ValueError:
            conn.close()
            flash("Amount must be a valid number.", "danger")
            return redirect(url_for("personal_plan.add_personal_plan_expense", plan_id=plan_id))

        conn.execute("""
            INSERT INTO personal_plan_expenses (plan_id, user_id, title, amount, category, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (plan_id, user_id, title, amount, category, note))
        conn.commit()
        conn.close()

        flash("Expense added successfully!", "success")
        return redirect(url_for("personal_plan.personal_plan_detail", plan_id=plan_id))

    categories = conn.execute("""
        SELECT name FROM categories
        WHERE user_id IS NULL OR user_id = ?
        ORDER BY user_id IS NULL DESC, name ASC
    """, (user_id,)).fetchall()
    conn.close()
    return render_template("personal_plans/add_expense.html", plan=plan, categories=categories)


@personal_plan_bp.route("/personal-plans/expense/<int:expense_id>/delete", methods=["POST"])
def delete_personal_plan_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    expense = conn.execute("""
        SELECT *
        FROM personal_plan_expenses
        WHERE id = ? AND user_id = ?
    """, (expense_id, user_id)).fetchone()

    if expense is None:
        conn.close()
        flash("Expense not found.", "danger")
        return redirect(url_for("personal_plan.list_personal_plans"))

    plan_id = expense["plan_id"]

    conn.execute("""
        DELETE FROM personal_plan_expenses
        WHERE id = ? AND user_id = ?
    """, (expense_id, user_id))
    conn.commit()
    conn.close()

    flash("Expense deleted successfully!", "success")
    return redirect(url_for("personal_plan.personal_plan_detail", plan_id=plan_id))


@personal_plan_bp.route("/personal-plans/<int:plan_id>/delete", methods=["POST"])
def delete_personal_plan(plan_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    plan = conn.execute("""
        SELECT *
        FROM personal_plans
        WHERE id = ? AND user_id = ?
    """, (plan_id, user_id)).fetchone()

    if plan is None:
        conn.close()
        flash("Plan not found.", "danger")
        return redirect(url_for("personal_plan.list_personal_plans"))

    conn.execute("""
        DELETE FROM personal_plan_expenses
        WHERE plan_id = ? AND user_id = ?
    """, (plan_id, user_id))

    conn.execute("""
        DELETE FROM personal_plans
        WHERE id = ? AND user_id = ?
    """, (plan_id, user_id))

    conn.commit()
    conn.close()

    flash("Plan deleted successfully!", "success")
    return redirect(url_for("personal_plan.list_personal_plans"))