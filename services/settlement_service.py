from db.connection import get_db_connection


def calculate_group_settlement(group_id):
    conn = get_db_connection()

    members = conn.execute("""
        SELECT users.id, users.username
        FROM group_members
        JOIN users ON users.id = group_members.user_id
        WHERE group_members.group_id = ?
    """, (group_id,)).fetchall()

    expenses = conn.execute("""
        SELECT *
        FROM group_expenses
        WHERE group_id = ?
        ORDER BY id ASC
    """, (group_id,)).fetchall()

    member_data = {}
    for member in members:
        member_data[member["id"]] = {
            "user_id": member["id"],
            "username": member["username"],
            "paid_total": 0.0,
            "owed_total": 0.0,
            "balance": 0.0
        }

    group_total = 0.0

    for expense in expenses:
        expense_id = expense["id"]
        paid_by = expense["paid_by"]
        amount = float(expense["amount"])

        group_total += amount

        if paid_by in member_data:
            member_data[paid_by]["paid_total"] += amount

        participants = conn.execute("""
            SELECT user_id
            FROM expense_participants
            WHERE expense_id = ?
        """, (expense_id,)).fetchall()

        participant_ids = [p["user_id"] for p in participants]

        if participant_ids:
            share = amount / len(participant_ids)

            for user_id in participant_ids:
                if user_id in member_data:
                    member_data[user_id]["owed_total"] += share

    for user_id in member_data:
        paid = member_data[user_id]["paid_total"]
        owed = member_data[user_id]["owed_total"]
        member_data[user_id]["balance"] = round(paid - owed, 2)
        member_data[user_id]["paid_total"] = round(paid, 2)
        member_data[user_id]["owed_total"] = round(owed, 2)

    debts = simplify_debts(member_data)

    conn.close()

    return {
        "group_total": round(group_total, 2),
        "members_summary": list(member_data.values()),
        "debts": debts
    }


def simplify_debts(member_data):
    creditors = []
    debtors = []

    for member in member_data.values():
        balance = round(member["balance"], 2)

        if balance > 0:
            creditors.append({
                "user_id": member["user_id"],
                "username": member["username"],
                "amount": balance
            })
        elif balance < 0:
            debtors.append({
                "user_id": member["user_id"],
                "username": member["username"],
                "amount": round(-balance, 2)
            })

    debts = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]

        pay_amount = min(debtor["amount"], creditor["amount"])
        pay_amount = round(pay_amount, 2)

        debts.append({
            "from_user_id": debtor["user_id"],
            "from_username": debtor["username"],
            "to_user_id": creditor["user_id"],
            "to_username": creditor["username"],
            "amount": pay_amount
        })

        debtor["amount"] = round(debtor["amount"] - pay_amount, 2)
        creditor["amount"] = round(creditor["amount"] - pay_amount, 2)

        if debtor["amount"] == 0:
            i += 1
        if creditor["amount"] == 0:
            j += 1

    return debts