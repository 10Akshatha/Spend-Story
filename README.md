# 💜 Spend Story – Multi-User Expense Tracker

Spend Story is a web-based expense management application built with Python and Flask. It helps users track daily expenses, manage monthly budgets, and plan upcoming expenses through a simple and user-friendly dashboard.

## ✨ Features

- **User Authentication:** Account registration and login.
- **Expense Management:** Add, view, edit and delete expenses.
- **Personalized Accounts:** Each user has separate expense records.
- **Budget Management:** Set and manage monthly budgets.
- **Expense Planner:** Record upcoming planned expenses.
- **Dashboard:** View and manage personal financial activity.
- **Data Storage:** SQLite database for local persistence.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web framework |
| SQLite | Database |
| HTML5 | Page structure |
| CSS3 | Styling |
| Jinja2 | Dynamic templates |

## 📁 Project Structure

```text
Spend-Story/
│
├── app.py
├── db.py
├── requirements.txt
├── .gitignore
│
├── templates/
│   ├── home.html
│   ├── login.html
│   └── register.html
│
└── static/
    └── style.css
```

## 🚀 Run Locally

1. Clone the repository:

```bash
git clone https://github.com/10Akshatha/Spend-Story.git
```

2. Navigate to the project:

```bash
cd Spend-Story
```

3. Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Set your Flask secret key (PowerShell):

```powershell
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

6. Run the application:

```bash
python app.py
```

7. Open your browser at:

`http://127.0.0.1:5000/`

## 🎯 Project Objective

To build a practical expense management application while learning backend development, database integration, authentication, and multi-user data management.

## 👩‍💻 Developer

**Akshatha DS**

GitHub: https://github.com/10Akshatha

Portfolio: https://github.com/10Akshatha/akshatha-portfolio