# DoubleR — Personal & Group Expense Manager

> A web-based expense management application built with Flask and SQLite,  
> inspired by Splitwise. Manage personal budgets and shared group expenses in one place.

---

##  Project Description

**DoubleR** allows users to track both personal and group expenses through a clean,  
modern interface. Users can create personal spending plans, form groups with friends,  
split bills automatically, and track who owes whom — all without any mobile app required.

---

##  Features

###  Authentication
- User registration and login with email + password
- Session-based authentication on every protected route
- Password visibility toggle on login and register pages

###  Personal Plans
- Create named spending plans (e.g. "Monthly Budget", "Trip to Almaty")
- Add, view, and delete expenses within each plan
- Real-time total balance displayed per plan
- Category tagging for each expense

###  Group Management
- Create groups and invite members by username
- Accept or reject group invitations via the Notifications inbox
- View all group members and their balances at a glance

###  Group Expenses
- Add shared expenses with three flexible split modes:
  - **All Members** — splits equally among everyone
  - **Selected Members** — choose specific people to split with
  - **Personal** — no split, just logged under your name
- Edit or delete any expense you added
- Category and note support per expense

###  Settlement Tracking
- Automatically calculates debt balances after each expense
- Dashboard cards: **Total**, **My Paid**, **I Owe**, **Owed To Me**
- Settlements page: mark individual debts as resolved (debtor + creditor both confirm)
- Debt summary visible directly on the group detail page

###  Category Management
- System-wide default categories available to all users
- Users can add their own custom categories
- Category manager accessible from every expense form via "+ Add Category"

###  Notifications
- Real-time badge on the navbar shows pending invitation count
- Notifications inbox lists all pending group invitations with sender and group info
- Badge count stays in sync with actual visible notifications

###  Timezone Support
- All timestamps stored in UTC, displayed in local system time
- Custom Jinja2 `localtime` filter applied globally

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask 3.1 |
| Frontend | HTML5, Bootstrap 5, Vanilla CSS |
| Database | SQLite (via Python `sqlite3`) |
| Templating | Jinja2 |
| Architecture | Flask Blueprints (MVC-like) |

---

##  Project Structure

```
DoubleR/
│
├── app.py                  # Application entry point, Jinja2 filters, context processors
├── config.py               # Secret key and configuration
├── requirements.txt        # Python dependencies
├── init_db.py              # Database initialisation script
│
├── db/
│   ├── connection.py       # Centralised DB connection helper
│   └── schema.sql          # Full database schema (9 tables)
│
├── routes/
│   ├── auth_routes.py      # Register, login, logout
│   ├── group_routes.py     # Groups, expenses, settlements, invitations
│   ├── personal_plan_routes.py  # Personal plans and plan expenses
│   ├── expense_routes.py   # Standalone personal expenses
│   ├── notification_routes.py   # Invitation inbox, accept/reject
│   └── category_routes.py  # Category list, add, delete
│
├── templates/
│   ├── base.html           # Shared layout with navbar
│   ├── index.html          # Landing / home page
│   ├── auth/               # login.html, register.html
│   ├── groups/             # list, detail, add_expense, edit_expense, settlements
│   ├── personal_plans/     # list, detail, add_expense
│   ├── notifications/      # notifications.html
│   ├── categories/         # categories.html
│   └── expenses/           # personal, add_personal, edit_personal

```

---

##  Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/hipsterjoker/DoubleR.git
cd DoubleR
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialise the database
```bash
python init_db.py
```

### 5. Run the application
```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

##  Database Schema

| Table | Purpose |
|-------|---------|
| `users` | User accounts (username, email, hashed password) |
| `groups` | Group metadata |
| `group_members` | Many-to-many: users ↔ groups |
| `group_expenses` | Shared expenses with split type |
| `expense_participants` | Which users share each expense |
| `settlements` | Debt records with dual-confirmation tracking |
| `personal_plans` | Named personal budget plans |
| `personal_plan_expenses` | Expenses within a personal plan |
| `categories` | System + user-defined expense categories |
| `invitations` | Group invitation tracking (pending/accepted/rejected) |

---

##  Default Test Accounts

> After running `init_db.py`, you can register your own accounts via the UI.  
> No seed data is inserted by default — create users and groups manually to test.

---

##  Team Members

| Name | Student ID |
|------|-----------|
| Rana Omarhan | 230103191 |
| Raziya Tulegenova | 230103011 |

---

*DoubleR — Final Project*
