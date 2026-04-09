# DoubleR Expense Manager

## 📌 Project Description

DoubleR Expense Manager is a simple web-based application developed using Flask.  
It helps users manage personal expenses and group expenses, similar to Splitwise.

The system allows users to:
- Register and login
- Track personal expenses
- Create groups
- Add and manage group expenses
- Split expenses between members
- Automatically calculate who owes whom

---

## 🚀 Features

### 1. User System
- User registration and login
- Session-based authentication

### 2. Personal Expense Management
- Add personal expenses
- Edit and delete expenses
- View expense list

### 3. Group Management
- Create groups
- Invite users to groups
- View group members

### 4. Group Expenses
- Add group expenses
- Edit and delete group expenses
- Different split types:
  - Personal (only yourself)
  - All members (equal split)
  - Selected members

### 5. Expense Settlement (Who owes whom)
- Automatically calculates:
  - Total paid by each user
  - Total share of each user
  - Final balance
- Displays:
  - Who you owe
  - Who owes you

### 6. Group Deletion
- Only group creator can delete a group
- All related data will be removed

---

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, Bootstrap
- **Database:** SQLite
- **Architecture:** MVC-like structure

---

## 📂 Project Structure
DoubleR/
│
├── app.py
├── config.py
├── requirements.txt
│
├── db/
│ ├── connection.py
│ ├── schema.sql
│ └── doubler.db
│
├── routes/
│ ├── auth_routes.py
│ ├── expense_routes.py
│ └── group_routes.py
│
├── services/
│ └── settlement_service.py
│
├── templates/
│ ├── base.html
│ ├── index.html
│ ├── auth/
│ ├── expenses/
│ └── groups/
│
└── static/
