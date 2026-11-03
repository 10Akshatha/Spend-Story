
import sqlite3


def create_table():
    connection = sqlite3.connect("expenses.db")

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL
            )
        """)

        connection.commit()
    finally:
        connection.close()

def check_all_expenses():
    connection = sqlite3.connect("expenses.db")

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, name, amount, category, date
            FROM expenses
            ORDER BY id DESC
        """)

        for row in cursor.fetchall():
            print(row)

    finally:
        connection.close()

def add_expense_to_db(name, amount, category, date):
    connection = sqlite3.connect("expenses.db")

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO expenses (name, amount, category, date)
            VALUES (?, ?, ?, ?)
        """, (name, amount, category, date))

        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def get_all_expenses():
    connection = sqlite3.connect("expenses.db")

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, name, amount, category, date
            FROM expenses
            ORDER BY id
        """)

        rows = cursor.fetchall()
        return [
            [name, amount, category, date, expense_id]
            for expense_id, name, amount, category, date in rows
        ]
    finally:
        connection.close()


def update_expense_in_db(expense_id, name, amount, category, date):
    connection = sqlite3.connect("expenses.db")

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE expenses
            SET name = ?, amount = ?, category = ?, date = ?
            WHERE id = ?
        """, (name, amount, category, date, expense_id))

        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


def delete_expense_from_db(expense_id):
    connection = sqlite3.connect("expenses.db")

    try:
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


create_table()
print("Database ready!")
check_all_expenses()

