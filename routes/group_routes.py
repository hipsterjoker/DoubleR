from flask import Blueprint, request, redirect, render_template, session, flash, url_for
from db.connection import get_db_connection

group_bp = Blueprint("group", __name__, url_prefix="/groups")


def get_group_members(conn, group_id):
    return conn.execute("""
        SELECT users.id, users.username
        FROM group_members
        JOIN users ON users.id = group_members.user_id
        WHERE group_members.group_id = ?
        ORDER BY users.username
    """, (group_id,)).fetchall()


def get_expense_participant_ids(conn, expense_id):
    rows = conn.execute("""
        SELECT user_id
        FROM expense_participants
        WHERE expense_id = ?
    """, (expense_id,)).fetchall()
    return [row["user_id"] for row in rows]


def build_participant_ids(conn, group_id, paid_by, split_type, form_data):
    member_rows = conn.execute("""
        SELECT user_id
        FROM group_members
        WHERE group_id = ?
    """, (group_id,)).fetchall()
    valid_member_ids = {row["user_id"] for row in member_rows}

    if split_type == "personal":
        return [paid_by]

    if split_type == "selected":
        selected_ids = form_data.getlist("participants")
        selected_ids = [int(uid) for uid in selected_ids]
        selected_ids = [uid for uid in selected_ids if uid in valid_member_ids]

        if not selected_ids:
            return None

        if paid_by not in selected_ids:
            selected_ids = [paid_by] + selected_ids

        return list(dict.fromkeys(selected_ids))

    if split_type == "all":
        return list(valid_member_ids)

    return None


def create_settlements_for_expense(conn, group_id, expense_id, paid_by, amount, participant_ids):
    conn.execute("""
        DELETE FROM settlements
        WHERE expense_id = ?
    """, (expense_id,))

    if not participant_ids or len(participant_ids) <= 1:
        return

    split_amount = round(float(amount) / len(participant_ids), 2)

    for uid in participant_ids:
        if uid == paid_by:
            continue

        conn.execute("""
            INSERT INTO settlements (
                group_id,
                expense_id,
                debtor_id,
                creditor_id,
                amount,
                debtor_checked,
                creditor_checked
            )
            VALUES (?, ?, ?, ?, ?, 0, 0)
        """, (
            group_id,
            expense_id,
            uid,
            paid_by,
            split_amount
        ))


@group_bp.route("/")
def list_groups():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        groups = conn.execute("""
            SELECT 
                g.*,
                COUNT(gm2.user_id) AS member_count
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            LEFT JOIN group_members gm2 ON g.id = gm2.group_id
            WHERE gm.user_id = ?
            GROUP BY g.id
            ORDER BY g.id DESC
        """, (user_id,)).fetchall()

        return render_template("groups/list.html", groups=groups)
    finally:
        conn.close()


@group_bp.route("/create", methods=["GET", "POST"])
def create_group():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        user_id = session["user_id"]

        if not name:
            flash("Group name cannot be empty.", "warning")
            return redirect(url_for("group.create_group"))

        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO groups (name, description, created_by)
                VALUES (?, ?, ?)
            """, (name, description, user_id))
            group_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO group_members (group_id, user_id)
                VALUES (?, ?)
            """, (group_id, user_id))

            conn.commit()
            flash("Group created successfully.", "success")
            return redirect(url_for("group.list_groups"))
        finally:
            conn.close()

    return render_template("groups/create.html")


@group_bp.route("/<int:group_id>")
def group_detail(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        membership = conn.execute("""
            SELECT *
            FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not membership:
            flash("You are not a member of this group.", "danger")
            return redirect(url_for("group.list_groups"))

        group = conn.execute("""
            SELECT *
            FROM groups
            WHERE id = ?
        """, (group_id,)).fetchone()

        members = get_group_members(conn, group_id)

        expenses = conn.execute("""
            SELECT group_expenses.*, users.username AS payer_name
            FROM group_expenses
            JOIN users ON users.id = group_expenses.paid_by
            WHERE group_expenses.group_id = ?
            ORDER BY group_expenses.id DESC
        """, (group_id,)).fetchall()

        total_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM group_expenses
            WHERE group_id = ?
        """, (group_id,)).fetchone()
        total = total_row["total"] if total_row else 0

        my_paid_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS paid_total
            FROM group_expenses
            WHERE group_id = ? AND paid_by = ?
        """, (group_id, user_id)).fetchone()
        my_paid_total = my_paid_row["paid_total"] if my_paid_row else 0

        my_owe_total_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS owe_total
            FROM settlements
            WHERE group_id = ? AND debtor_id = ?
              AND NOT (debtor_checked = 1 AND creditor_checked = 1)
        """, (group_id, user_id)).fetchone()
        my_owe_total = my_owe_total_row["owe_total"] if my_owe_total_row else 0

        owes_me_total_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS owes_me_total
            FROM settlements
            WHERE group_id = ? AND creditor_id = ?
              AND NOT (debtor_checked = 1 AND creditor_checked = 1)
        """, (group_id, user_id)).fetchone()
        owes_me_total = owes_me_total_row["owes_me_total"] if owes_me_total_row else 0

        my_summary = {
            "user_id": user_id,
            "paid": my_paid_total,
            "owe": my_owe_total,
            "owed_to_me": owes_me_total
        }

        my_debts = conn.execute("""
            SELECT
                s.*,
                ge.title AS expense_title,
                debtor.username AS debtor_name,
                creditor.username AS creditor_name
            FROM settlements s
            JOIN group_expenses ge ON ge.id = s.expense_id
            JOIN users debtor ON debtor.id = s.debtor_id
            JOIN users creditor ON creditor.id = s.creditor_id
            WHERE s.group_id = ? AND s.debtor_id = ?
            ORDER BY s.id DESC
        """, (group_id, user_id)).fetchall()

        owes_me = conn.execute("""
            SELECT
                s.*,
                ge.title AS expense_title,
                debtor.username AS debtor_name,
                creditor.username AS creditor_name
            FROM settlements s
            JOIN group_expenses ge ON ge.id = s.expense_id
            JOIN users debtor ON debtor.id = s.debtor_id
            JOIN users creditor ON creditor.id = s.creditor_id
            WHERE s.group_id = ? AND s.creditor_id = ?
            ORDER BY s.id DESC
        """, (group_id, user_id)).fetchall()

        return render_template(
            "groups/detail.html",
            group=group,
            members=members,
            expenses=expenses,
            total=total,
            my_summary=my_summary,
            my_debts=my_debts,
            owes_me=owes_me,
        )
    finally:
        conn.close()


@group_bp.route("/<int:group_id>/add", methods=["GET", "POST"])
def add_group_expense(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        membership = conn.execute("""
            SELECT *
            FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not membership:
            flash("You are not a member of this group.", "danger")
            return redirect(url_for("group.list_groups"))

        group = conn.execute("""
            SELECT *
            FROM groups
            WHERE id = ?
        """, (group_id,)).fetchone()

        members = get_group_members(conn, group_id)

        if request.method == "POST":
            title = request.form["title"].strip()
            amount_raw = request.form["amount"]
            category = request.form.get("category", "").strip()
            note = request.form.get("note", "").strip()
            split_type = request.form["split_type"]

            if not title:
                flash("Title cannot be empty.", "warning")
                return redirect(url_for("group.add_group_expense", group_id=group_id))

            try:
                amount = float(amount_raw)
            except ValueError:
                flash("Invalid amount.", "danger")
                return redirect(url_for("group.add_group_expense", group_id=group_id))

            if amount <= 0:
                flash("Amount must be greater than 0.", "warning")
                return redirect(url_for("group.add_group_expense", group_id=group_id))

            cursor = conn.execute("""
                INSERT INTO group_expenses (group_id, paid_by, title, amount, category, note, split_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (group_id, user_id, title, amount, category, note, split_type))

            expense_id = cursor.lastrowid

            participant_ids = build_participant_ids(conn, group_id, user_id, split_type, request.form)

            if participant_ids is None:
                conn.rollback()
                flash("Please select valid participants.", "warning")
                return redirect(url_for("group.add_group_expense", group_id=group_id))

            for uid in participant_ids:
                conn.execute("""
                    INSERT INTO expense_participants (expense_id, user_id)
                    VALUES (?, ?)
                """, (expense_id, uid))

            create_settlements_for_expense(conn, group_id, expense_id, user_id, amount, participant_ids)

            conn.commit()
            flash("Group expense added.", "success")
            return redirect(url_for("group.group_detail", group_id=group_id))

        categories = conn.execute("""
            SELECT name FROM categories
            WHERE user_id IS NULL OR user_id = ?
            ORDER BY user_id IS NULL DESC, name ASC
        """, (user_id,)).fetchall()

        return render_template(
            "groups/add_expense.html",
            group=group,
            members=members,
            categories=categories
        )
    finally:
        conn.close()


@group_bp.route("/<int:group_id>/invite", methods=["POST"])
def invite_member(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    current_user_id = session["user_id"]
    username = request.form["username"].strip()

    conn = get_db_connection()

    try:
        membership = conn.execute("""
            SELECT *
            FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, current_user_id)).fetchone()

        if not membership:
            flash("You are not allowed to invite members.", "danger")
            return redirect(url_for("group.list_groups"))

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("group.group_detail", group_id=group_id))

        already_member = conn.execute("""
            SELECT id FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user["id"])).fetchone()

        if already_member:
            flash("This user is already in the group.", "warning")
            return redirect(url_for("group.group_detail", group_id=group_id))

        pending = conn.execute("""
            SELECT id FROM invitations
            WHERE group_id = ? AND receiver_id = ? AND status = 'pending'
        """, (group_id, user["id"])).fetchone()

        if pending:
            flash("An invitation is already pending for this user.", "warning")
            return redirect(url_for("group.group_detail", group_id=group_id))

        conn.execute("""
            INSERT INTO invitations (group_id, sender_id, receiver_id, status)
            VALUES (?, ?, ?, 'pending')
        """, (group_id, current_user_id, user["id"]))

        conn.commit()
        flash("Invitation sent. They will see it in Notifications.", "success")
        return redirect(url_for("group.group_detail", group_id=group_id))
    finally:
        conn.close()


@group_bp.route("/expense/delete/<int:expense_id>/<int:group_id>", methods=["POST"])
def delete_group_expense(expense_id, group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        member = conn.execute("""
            SELECT *
            FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not member:
            flash("Access denied.", "danger")
            return redirect(url_for("group.list_groups"))

        conn.execute("""
            DELETE FROM settlements
            WHERE expense_id = ?
        """, (expense_id,))

        conn.execute("""
            DELETE FROM expense_participants
            WHERE expense_id = ?
        """, (expense_id,))

        conn.execute("""
            DELETE FROM group_expenses
            WHERE id = ? AND group_id = ?
        """, (expense_id, group_id))

        conn.commit()
        flash("Expense deleted.", "success")
        return redirect(url_for("group.group_detail", group_id=group_id))
    finally:
        conn.close()


@group_bp.route("/expense/edit/<int:expense_id>/<int:group_id>", methods=["GET", "POST"])
def edit_group_expense(expense_id, group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        member = conn.execute("""
            SELECT *
            FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not member:
            flash("Access denied.", "danger")
            return redirect(url_for("group.list_groups"))

        expense = conn.execute("""
            SELECT *
            FROM group_expenses
            WHERE id = ? AND group_id = ?
        """, (expense_id, group_id)).fetchone()

        if not expense:
            flash("Expense not found.", "danger")
            return redirect(url_for("group.group_detail", group_id=group_id))

        group = conn.execute("""
            SELECT *
            FROM groups
            WHERE id = ?
        """, (group_id,)).fetchone()

        members = get_group_members(conn, group_id)
        selected_participant_ids = get_expense_participant_ids(conn, expense_id)

        if request.method == "POST":
            title = request.form["title"].strip()
            amount_raw = request.form["amount"]
            split_type = request.form["split_type"]

            if not title:
                flash("Title cannot be empty.", "warning")
                return redirect(url_for("group.edit_group_expense", expense_id=expense_id, group_id=group_id))

            try:
                amount = float(amount_raw)
            except ValueError:
                flash("Invalid amount.", "danger")
                return redirect(url_for("group.edit_group_expense", expense_id=expense_id, group_id=group_id))

            if amount <= 0:
                flash("Amount must be greater than 0.", "warning")
                return redirect(url_for("group.edit_group_expense", expense_id=expense_id, group_id=group_id))

            paid_by = expense["paid_by"]
            participant_ids = build_participant_ids(conn, group_id, paid_by, split_type, request.form)

            if participant_ids is None:
                flash("Please select valid participants.", "warning")
                return redirect(url_for("group.edit_group_expense", expense_id=expense_id, group_id=group_id))

            conn.execute("""
                UPDATE group_expenses
                SET title = ?, amount = ?, split_type = ?
                WHERE id = ? AND group_id = ?
            """, (title, amount, split_type, expense_id, group_id))

            conn.execute("""
                DELETE FROM expense_participants
                WHERE expense_id = ?
            """, (expense_id,))

            for uid in participant_ids:
                conn.execute("""
                    INSERT INTO expense_participants (expense_id, user_id)
                    VALUES (?, ?)
                """, (expense_id, uid))

            create_settlements_for_expense(conn, group_id, expense_id, paid_by, amount, participant_ids)

            conn.commit()
            flash("Expense updated.", "success")
            return redirect(url_for("group.group_detail", group_id=group_id))

        categories = conn.execute("""
            SELECT name FROM categories
            WHERE user_id IS NULL OR user_id = ?
            ORDER BY user_id IS NULL DESC, name ASC
        """, (user_id,)).fetchall()

        return render_template(
            "groups/edit_expense.html",
            expense=expense,
            group=group,
            group_id=group_id,
            members=members,
            selected_participant_ids=selected_participant_ids,
            categories=categories
        )
    finally:
        conn.close()


@group_bp.route("/delete/<int:group_id>", methods=["POST"])
def delete_group(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        group = conn.execute("""
            SELECT *
            FROM groups
            WHERE id = ?
        """, (group_id,)).fetchone()

        if not group:
            flash("Group not found.", "danger")
            return redirect(url_for("group.list_groups"))

        if group["created_by"] != user_id:
            flash("Only the group creator can delete this group.", "danger")
            return redirect(url_for("group.group_detail", group_id=group_id))

        expense_ids = conn.execute("""
            SELECT id
            FROM group_expenses
            WHERE group_id = ?
        """, (group_id,)).fetchall()

        for expense_id in expense_ids:
            conn.execute("""
                DELETE FROM settlements
                WHERE expense_id = ?
            """, (expense_id["id"],))

            conn.execute("""
                DELETE FROM expense_participants
                WHERE expense_id = ?
            """, (expense_id["id"],))

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
        flash("Group deleted successfully.", "success")
        return redirect(url_for("group.list_groups"))
    finally:
        conn.close()


@group_bp.route("/<int:group_id>/settlements")
def group_settlements(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        membership = conn.execute("""
            SELECT * FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not membership:
            flash("You are not a member of this group.", "danger")
            return redirect(url_for("group.list_groups"))

        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()

        settlements = conn.execute("""
            SELECT
                s.*,
                ge.title AS expense_title,
                debtor.username AS debtor_name,
                creditor.username AS creditor_name
            FROM settlements s
            JOIN group_expenses ge ON ge.id = s.expense_id
            JOIN users debtor ON debtor.id = s.debtor_id
            JOIN users creditor ON creditor.id = s.creditor_id
            WHERE s.group_id = ?
            ORDER BY (s.debtor_checked = 1 AND s.creditor_checked = 1) ASC, s.id DESC
        """, (group_id,)).fetchall()

        return render_template(
            "groups/settlements.html",
            group=group,
            settlements=settlements,
            user_id=user_id
        )
    finally:
        conn.close()


@group_bp.route("/toggle-page/<int:settlement_id>/<int:group_id>", methods=["POST"])
def toggle_settlement_page(settlement_id, group_id):
    """Same as toggle_settlement but redirects back to the settlements page."""
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        settlement = conn.execute("""
            SELECT * FROM settlements
            WHERE id = ? AND group_id = ?
        """, (settlement_id, group_id)).fetchone()

        if not settlement:
            flash("Settlement record not found.", "danger")
            return redirect(url_for("group.group_settlements", group_id=group_id))

        membership = conn.execute("""
            SELECT * FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not membership:
            flash("Access denied.", "danger")
            return redirect(url_for("group.list_groups"))

        if settlement["debtor_id"] == user_id:
            new_value = 0 if settlement["debtor_checked"] == 1 else 1
            conn.execute(
                "UPDATE settlements SET debtor_checked = ? WHERE id = ?",
                (new_value, settlement_id)
            )
            flash("Payment confirmation updated.", "success")

        elif settlement["creditor_id"] == user_id:
            new_value = 0 if settlement["creditor_checked"] == 1 else 1
            conn.execute(
                "UPDATE settlements SET creditor_checked = ? WHERE id = ?",
                (new_value, settlement_id)
            )
            flash("Receipt confirmation updated.", "success")

        else:
            flash("You are not part of this settlement.", "danger")
            return redirect(url_for("group.group_settlements", group_id=group_id))

        conn.commit()
        return redirect(url_for("group.group_settlements", group_id=group_id))
    finally:
        conn.close()


@group_bp.route("/<int:group_id>/leave", methods=["POST"])
def leave_group(group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()

        if not group:
            flash("Group not found.", "danger")
            return redirect(url_for("group.list_groups"))

        if group["created_by"] == user_id:
            flash("You are the creator. Delete the group instead of leaving.", "warning")
            return redirect(url_for("group.group_detail", group_id=group_id))

        membership = conn.execute("""
            SELECT * FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not membership:
            flash("You are not a member of this group.", "danger")
            return redirect(url_for("group.list_groups"))

        conn.execute("""
            DELETE FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))

        conn.commit()
        flash("You have left the group. Your past records remain visible to others.", "success")
        return redirect(url_for("group.list_groups"))
    finally:
        conn.close()


@group_bp.route("/toggle/<int:settlement_id>/<int:group_id>", methods=["POST"])
def toggle_settlement(settlement_id, group_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    try:
        settlement = conn.execute("""
            SELECT *
            FROM settlements
            WHERE id = ? AND group_id = ?
        """, (settlement_id, group_id)).fetchone()

        if not settlement:
            flash("Settlement record not found.", "danger")
            return redirect(url_for("group.group_detail", group_id=group_id))

        membership = conn.execute("""
            SELECT *
            FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id)).fetchone()

        if not membership:
            flash("Access denied.", "danger")
            return redirect(url_for("group.list_groups"))

        if settlement["debtor_id"] == user_id:
            new_value = 0 if settlement["debtor_checked"] == 1 else 1
            conn.execute("""
                UPDATE settlements
                SET debtor_checked = ?
                WHERE id = ?
            """, (new_value, settlement_id))
            flash("Your payment confirmation was updated.", "success")

        elif settlement["creditor_id"] == user_id:
            new_value = 0 if settlement["creditor_checked"] == 1 else 1
            conn.execute("""
                UPDATE settlements
                SET creditor_checked = ?
                WHERE id = ?
            """, (new_value, settlement_id))
            flash("Your receipt confirmation was updated.", "success")

        else:
            flash("You are not allowed to update this settlement.", "danger")
            return redirect(url_for("group.group_detail", group_id=group_id))

        conn.commit()
        return redirect(url_for("group.group_detail", group_id=group_id))
    finally:
        conn.close()