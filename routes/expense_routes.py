from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from db.connection import get_db_connection

expense_bp = Blueprint("expense", __name__, url_prefix="/expenses")


@expense_bp.route("/personal")
def personal_expenses():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    expenses = conn.execute("""
        SELECT * FROM personal_expenses
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    total = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM personal_expenses
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    conn.close()
    return render_template(
        "expenses/personal.html",
        expenses=expenses,
        total=total["total"]
    )


@expense_bp.route("/personal/add", methods=["GET", "POST"])
def add_personal_expense():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form["title"]
        amount = float(request.form["amount"])
        category = request.form["category"]
        user_id = session["user_id"]

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO personal_expenses (user_id, title, amount, category)
            VALUES (?, ?, ?, ?)
        """, (user_id, title, amount, category))
        conn.commit()
        conn.close()

        flash("Personal expense added successfully.", "success")
        return redirect(url_for("expense.personal_expenses"))

    return render_template("expenses/add_personal.html")


@expense_bp.route("/personal/delete/<int:expense_id>")
def delete_personal_expense(expense_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db_connection()

    expense = conn.execute(
        "SELECT * FROM personal_expenses WHERE id = ? AND user_id = ?",
        (expense_id, session["user_id"])
    ).fetchone()

    if expense:
        conn.execute(
            "DELETE FROM personal_expenses WHERE id = ? AND user_id = ?",
            (expense_id, session["user_id"])
        )
        conn.commit()
        flash("Expense deleted successfully.", "success")
    else:
        flash("Unauthorized action.", "danger")

    conn.close()
    return redirect(url_for("expense.personal_expenses"))


@expense_bp.route("/personal/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_personal_expense(expense_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db_connection()

    expense = conn.execute(
        "SELECT * FROM personal_expenses WHERE id = ? AND user_id = ?",
        (expense_id, session["user_id"])
    ).fetchone()

    if not expense:
        conn.close()
        flash("Unauthorized access.", "danger")
        return redirect(url_for("expense.personal_expenses"))

    if request.method == "POST":
        title = request.form["title"]
        amount = float(request.form["amount"])
        category = request.form["category"]

        conn.execute("""
            UPDATE personal_expenses
            SET title = ?, amount = ?, category = ?
            WHERE id = ? AND user_id = ?
        """, (title, amount, category, expense_id, session["user_id"]))

        conn.commit()
        conn.close()

        flash("Expense updated successfully.", "success")
        return redirect(url_for("expense.personal_expenses"))

    conn.close()
    return render_template("expenses/edit_personal.html", expense=expense)