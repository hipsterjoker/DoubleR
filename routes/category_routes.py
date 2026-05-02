from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.connection import get_db_connection

category_bp = Blueprint("category", __name__, url_prefix="/categories")


def get_user_categories(conn, user_id):
    """Return system categories + categories belonging to this user."""
    return conn.execute("""
        SELECT * FROM categories
        WHERE user_id IS NULL OR user_id = ?
        ORDER BY user_id IS NULL DESC, name ASC
    """, (user_id,)).fetchall()


def _categories_redirect(next_url=""):
    """Redirect back to the categories page, preserving the next param."""
    base = url_for("category.list_categories")
    if next_url:
        return redirect(f"{base}?next={next_url}")
    return redirect(base)


@category_bp.route("/")
def list_categories():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    try:
        categories = conn.execute("""
            SELECT * FROM categories
            WHERE user_id IS NULL OR user_id = ?
            ORDER BY user_id IS NULL DESC, name ASC
        """, (user_id,)).fetchall()
        return render_template("categories/categories.html", categories=categories)
    finally:
        conn.close()


@category_bp.route("/add", methods=["POST"])
def add_category():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    name = request.form.get("name", "").strip()
    next_url = request.form.get("next", "")
    user_id = session["user_id"]

    if not name:
        flash("Category name cannot be empty.", "warning")
        return _categories_redirect(next_url)

    conn = get_db_connection()
    try:
        existing = conn.execute("""
            SELECT id FROM categories
            WHERE name = ? AND (user_id IS NULL OR user_id = ?)
        """, (name, user_id)).fetchone()

        if existing:
            flash("That category already exists.", "warning")
            return _categories_redirect(next_url)

        conn.execute(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        conn.commit()
        flash("Category added.", "success")
    finally:
        conn.close()

    return _categories_redirect(next_url)


@category_bp.route("/delete/<int:cat_id>", methods=["POST"])
def delete_category(cat_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    next_url = request.form.get("next", "")
    user_id = session["user_id"]
    conn = get_db_connection()
    try:
        cat = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (cat_id,)
        ).fetchone()

        if not cat:
            flash("Category not found.", "danger")
            return _categories_redirect(next_url)

        if cat["user_id"] is None:
            flash("System categories cannot be deleted.", "danger")
            return _categories_redirect(next_url)

        if cat["user_id"] != user_id:
            flash("Access denied.", "danger")
            return _categories_redirect(next_url)

        conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        flash("Category deleted.", "success")
    finally:
        conn.close()

    return _categories_redirect(next_url)
