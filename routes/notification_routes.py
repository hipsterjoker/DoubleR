from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.connection import get_db_connection

notification_bp = Blueprint("notification", __name__, url_prefix="/notifications")


@notification_bp.route("/")
def notifications():
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    try:
        invitations = conn.execute("""
            SELECT
                i.*,
                g.name AS group_name,
                u.username AS sender_name
            FROM invitations i
            JOIN groups g ON g.id = i.group_id
            JOIN users u ON u.id = i.sender_id
            WHERE i.receiver_id = ? AND i.status = 'pending'
            ORDER BY i.created_at DESC
        """, (user_id,)).fetchall()

        return render_template("notifications/notifications.html", invitations=invitations)
    finally:
        conn.close()


@notification_bp.route("/invite/<int:inv_id>/accept", methods=["POST"])
def accept_invitation(inv_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    try:
        invitation = conn.execute(
            "SELECT * FROM invitations WHERE id = ? AND receiver_id = ? AND status = 'pending'",
            (inv_id, user_id)
        ).fetchone()

        if not invitation:
            flash("Invitation not found or already handled.", "warning")
            return redirect(url_for("notification.notifications"))

        already_member = conn.execute(
            "SELECT id FROM group_members WHERE group_id = ? AND user_id = ?",
            (invitation["group_id"], user_id)
        ).fetchone()

        if not already_member:
            conn.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
                (invitation["group_id"], user_id)
            )

        conn.execute(
            "UPDATE invitations SET status = 'accepted' WHERE id = ?",
            (inv_id,)
        )
        conn.commit()
        flash("You have joined the group!", "success")
    finally:
        conn.close()

    return redirect(url_for("notification.notifications"))


@notification_bp.route("/invite/<int:inv_id>/reject", methods=["POST"])
def reject_invitation(inv_id):
    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    try:
        invitation = conn.execute(
            "SELECT * FROM invitations WHERE id = ? AND receiver_id = ? AND status = 'pending'",
            (inv_id, user_id)
        ).fetchone()

        if not invitation:
            flash("Invitation not found or already handled.", "warning")
            return redirect(url_for("notification.notifications"))

        conn.execute(
            "UPDATE invitations SET status = 'rejected' WHERE id = ?",
            (inv_id,)
        )
        conn.commit()
        flash("Invitation rejected.", "success")
    finally:
        conn.close()

    return redirect(url_for("notification.notifications"))
