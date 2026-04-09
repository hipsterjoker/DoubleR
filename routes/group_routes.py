from flask import Blueprint, request, redirect, render_template, session, flash, url_for
from db.connection import get_db_connection
from services.settlement_service import calculate_group_settlement

group_bp = Blueprint("group", __name__, url_prefix="/groups")


@group_bp.route("/")
def list_groups():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    groups = conn.execute("""
        SELECT groups.*
        FROM groups
        JOIN group_members ON groups.id = group_members.group_id
        WHERE group_members.user_id = ?
        ORDER BY groups.id DESC
    """, (user_id,)).fetchall()

    conn.close()
    return render_template("groups/list.html", groups=groups)


@group_bp.route("/create", methods=["GET", "POST"])
def create_group():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form["name"]
        user_id = session["user_id"]

        conn = get_db_connection()

        cursor = conn.execute(
            "INSERT INTO groups (name, created_by) VALUES (?, ?)",
            (name, user_id)
        )
        group_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
            (group_id, user_id)
        )

        conn.commit()
        conn.close()

        flash("Group created successfully.", "success")
        return redirect(url_for("group.list_groups"))

    return render_template("groups/create.html")


@group_bp.route("/<int:group_id>", methods=["GET", "POST"])
def group_detail(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    membership = conn.execute("""
        SELECT * FROM group_members
        WHERE group_id = ? AND user_id = ?
    """, (group_id, user_id)).fetchone()

    if not membership:
        conn.close()
        flash("You are not a member of this group.", "danger")
        return redirect(url_for("group.list_groups"))

    if request.method == "POST":
        title = request.form["title"]
        amount = float(request.form["amount"])
        split_type = request.form["split_type"]

        cursor = conn.execute("""
            INSERT INTO group_expenses (group_id, paid_by, title, amount, split_type)
            VALUES (?, ?, ?, ?, ?)
        """, (group_id, user_id, title, amount, split_type))

        expense_id = cursor.lastrowid

        if split_type == "personal":
            participant_ids = [user_id]

        elif split_type == "selected":
            selected_ids = request.form.getlist("participants")
            selected_ids = [int(uid) for uid in selected_ids]

            if not selected_ids:
                conn.rollback()
                conn.close()
                flash("Please select at least one other member.", "warning")
                return redirect(url_for("group.group_detail", group_id=group_id))

            participant_ids = [user_id] + selected_ids

        elif split_type == "all":
            members_all = conn.execute("""
                SELECT user_id
                FROM group_members
                WHERE group_id = ?
            """, (group_id,)).fetchall()

            participant_ids = [m["user_id"] for m in members_all]

        else:
            conn.rollback()
            conn.close()
            flash("Invalid split type.", "danger")
            return redirect(url_for("group.group_detail", group_id=group_id))

        for uid in participant_ids:
            conn.execute("""
                INSERT INTO expense_participants (expense_id, user_id)
                VALUES (?, ?)
            """, (expense_id, uid))

        conn.commit()
        flash("Group expense added.", "success")
        return redirect(url_for("group.group_detail", group_id=group_id))

    group = conn.execute(
        "SELECT * FROM groups WHERE id = ?",
        (group_id,)
    ).fetchone()

    members = conn.execute("""
        SELECT users.id, users.username
        FROM group_members
        JOIN users ON users.id = group_members.user_id
        WHERE group_members.group_id = ?
    """, (group_id,)).fetchall()

    expenses = conn.execute("""
        SELECT group_expenses.*, users.username AS payer_name
        FROM group_expenses
        JOIN users ON users.id = group_expenses.paid_by
        WHERE group_expenses.group_id = ?
        ORDER BY group_expenses.id DESC
    """, (group_id,)).fetchall()

    conn.close()

    settlement_data = calculate_group_settlement(group_id)

    my_summary = None
    my_debts = []
    owes_me = []

    for item in settlement_data["members_summary"]:
        if item["user_id"] == user_id:
            my_summary = item
            break

    for debt in settlement_data["debts"]:
        if debt["from_user_id"] == user_id:
            my_debts.append(debt)
        if debt["to_user_id"] == user_id:
            owes_me.append(debt)

    return render_template(
        "groups/detail.html",
        group=group,
        members=members,
        expenses=expenses,
        total=settlement_data["group_total"],
        members_summary=settlement_data["members_summary"],
        debts=settlement_data["debts"],
        my_summary=my_summary,
        my_debts=my_debts,
        owes_me=owes_me
    )


@group_bp.route("/<int:group_id>/invite", methods=["POST"])
def invite_member(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    current_user_id = session["user_id"]
    username = request.form["username"]

    conn = get_db_connection()

    membership = conn.execute("""
        SELECT * FROM group_members
        WHERE group_id = ? AND user_id = ?
    """, (group_id, current_user_id)).fetchone()

    if not membership:
        conn.close()
        flash("You are not allowed to invite members.", "danger")
        return redirect(url_for("group.list_groups"))

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user:
        conn.close()
        flash("User not found.", "danger")
        return redirect(url_for("group.group_detail", group_id=group_id))

    existing = conn.execute("""
        SELECT * FROM group_members
        WHERE group_id = ? AND user_id = ?
    """, (group_id, user["id"])).fetchone()

    if existing:
        conn.close()
        flash("This user is already in the group.", "warning")
        return redirect(url_for("group.group_detail", group_id=group_id))

    conn.execute(
        "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
        (group_id, user["id"])
    )
    conn.commit()
    conn.close()

    flash("User invited successfully.", "success")
    return redirect(url_for("group.group_detail", group_id=group_id))


@group_bp.route("/expense/delete/<int:expense_id>/<int:group_id>")
def delete_group_expense(expense_id, group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    member = conn.execute(
        "SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, user_id)
    ).fetchone()

    if not member:
        conn.close()
        flash("Access denied.", "danger")
        return redirect(url_for("group.list_groups"))

    conn.execute(
        "DELETE FROM expense_participants WHERE expense_id = ?",
        (expense_id,)
    )

    conn.execute(
        "DELETE FROM group_expenses WHERE id = ? AND group_id = ?",
        (expense_id, group_id)
    )

    conn.commit()
    conn.close()

    flash("Expense deleted.", "success")
    return redirect(url_for("group.group_detail", group_id=group_id))


@group_bp.route("/expense/edit/<int:expense_id>/<int:group_id>", methods=["GET", "POST"])
def edit_group_expense(expense_id, group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    member = conn.execute(
        "SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, user_id)
    ).fetchone()

    if not member:
        conn.close()
        flash("Access denied.", "danger")
        return redirect(url_for("group.list_groups"))

    expense = conn.execute(
        "SELECT * FROM group_expenses WHERE id = ? AND group_id = ?",
        (expense_id, group_id)
    ).fetchone()

    if not expense:
        conn.close()
        flash("Expense not found.", "danger")
        return redirect(url_for("group.group_detail", group_id=group_id))

    members = conn.execute("""
        SELECT users.id, users.username
        FROM group_members
        JOIN users ON users.id = group_members.user_id
        WHERE group_members.group_id = ?
    """, (group_id,)).fetchall()

    selected_participants = conn.execute("""
        SELECT user_id
        FROM expense_participants
        WHERE expense_id = ?
    """, (expense_id,)).fetchall()

    selected_participant_ids = [row["user_id"] for row in selected_participants]

    if request.method == "POST":
        title = request.form["title"]
        amount = float(request.form["amount"])
        split_type = request.form["split_type"]

        conn.execute("""
            UPDATE group_expenses
            SET title = ?, amount = ?, split_type = ?
            WHERE id = ? AND group_id = ?
        """, (title, amount, split_type, expense_id, group_id))

        conn.execute("""
            DELETE FROM expense_participants
            WHERE expense_id = ?
        """, (expense_id,))

        if split_type == "personal":
            participant_ids = [expense["paid_by"]]

        elif split_type == "selected":
            selected_ids = request.form.getlist("participants")
            selected_ids = [int(uid) for uid in selected_ids]

            if not selected_ids:
                conn.rollback()
                conn.close()
                flash("Please select at least one other member.", "warning")
                return redirect(url_for("group.edit_group_expense", expense_id=expense_id, group_id=group_id))

            participant_ids = [expense["paid_by"]] + selected_ids

        elif split_type == "all":
            members_all = conn.execute("""
                SELECT user_id
                FROM group_members
                WHERE group_id = ?
            """, (group_id,)).fetchall()

            participant_ids = [m["user_id"] for m in members_all]

        else:
            conn.rollback()
            conn.close()
            flash("Invalid split type.", "danger")
            return redirect(url_for("group.edit_group_expense", expense_id=expense_id, group_id=group_id))

        for uid in participant_ids:
            conn.execute("""
                INSERT INTO expense_participants (expense_id, user_id)
                VALUES (?, ?)
            """, (expense_id, uid))

        conn.commit()
        conn.close()

        flash("Expense updated.", "success")
        return redirect(url_for("group.group_detail", group_id=group_id))

    conn.close()
    return render_template(
        "groups/edit_expense.html",
        expense=expense,
        group_id=group_id,
        members=members,
        selected_participant_ids=selected_participant_ids
    )



@group_bp.route("/delete/<int:group_id>", methods=["POST"])
def delete_group(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    group = conn.execute("""
        SELECT * FROM groups
        WHERE id = ?
    """, (group_id,)).fetchone()

    if not group:
        conn.close()
        flash("Group not found.", "danger")
        return redirect(url_for("group.list_groups"))

    if group["created_by"] != user_id:
        conn.close()
        flash("Only the group creator can delete this group.", "danger")
        return redirect(url_for("group.group_detail", group_id=group_id))

    expense_ids = conn.execute("""
        SELECT id FROM group_expenses
        WHERE group_id = ?
    """, (group_id,)).fetchall()

    expense_id_list = [row["id"] for row in expense_ids]

    for expense_id in expense_id_list:
        conn.execute("""
            DELETE FROM expense_participants
            WHERE expense_id = ?
        """, (expense_id,))

    conn.execute("""
        DELETE FROM settlements
        WHERE group_id = ?
    """, (group_id,))

    conn.execute("""
        DELETE FROM group_expenses
        WHERE group_id = ?
    """, (group_id,))

    conn.execute("""
        DELETE FROM group_members
        WHERE group_id = ?
    """, (group_id,))

    conn.execute("""
        DELETE FROM groups
        WHERE id = ?
    """, (group_id,))

    conn.commit()
    conn.close()

    flash("Group deleted successfully.", "success")
    return redirect(url_for("group.list_groups"))