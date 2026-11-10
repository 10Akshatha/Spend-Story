
import os
import sqlite3

# Use the project folder for the local database.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "expenses.db")
)


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def column_exists(connection, table, column):
    columns = connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(row["name"] == column for row in columns)


def migrate_budgets(connection):
    """Ensure budgets are unique per user and month."""

    columns = connection.execute(
        "PRAGMA table_info(budgets)"
    ).fetchall()

    if not columns:
        connection.execute("""
            CREATE TABLE budgets (
                user_id INTEGER REFERENCES users(id),
                month_key TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                PRIMARY KEY (user_id, month_key)
            )
        """)
        return

    # Check whether the existing table already has the correct
    # composite primary key: user_id + month_key.
    primary_keys = {
        row["name"]: row["pk"]
        for row in columns
    }

    correct_primary_key = (
        primary_keys.get("user_id") == 1
        and primary_keys.get("month_key") == 2
    )

    if correct_primary_key:
        return

    has_user_id = "user_id" in primary_keys

    connection.execute("""
        CREATE TABLE budgets_new (
            user_id INTEGER REFERENCES users(id),
            month_key TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            PRIMARY KEY (user_id, month_key)
        )
    """)

    if has_user_id:
        connection.execute("""
            INSERT INTO budgets_new (user_id, month_key, amount)
            SELECT user_id, month_key, amount
            FROM budgets
        """)
    else:
        connection.execute("""
            INSERT INTO budgets_new (user_id, month_key, amount)
            SELECT NULL, month_key, amount
            FROM budgets
        """)

    connection.execute("DROP TABLE budgets")
    connection.execute(
        "ALTER TABLE budgets_new RENAME TO budgets"
    )


def create_table():
    connection = get_connection()

    try:
        # Keep the schema changes together in one transaction.
        connection.execute("BEGIN IMMEDIATE")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL
            )
        """)

        if not column_exists(connection, "expenses", "user_id"):
            connection.execute("""
                ALTER TABLE expenses
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """)

        migrate_budgets(connection)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS planned_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                planned_date TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)

        if not column_exists(
            connection, "planned_expenses", "user_id"
        ):
            connection.execute("""
                ALTER TABLE planned_expenses
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_user
            ON expenses(user_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_plans_user
            ON planned_expenses(user_id)
        """)

        connection.commit()
        print("Database schema is ready.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def create_user(name, email, password_hash):
    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        # Only the first account may claim existing unassigned data.
        existing_user = connection.execute(
            "SELECT id FROM users LIMIT 1"
        ).fetchone()

        cursor = connection.execute("""
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
        """, (
            name.strip(),
            email.strip().lower(),
            password_hash
        ))

        user_id = cursor.lastrowid

        if existing_user is None:
            connection.execute("""
                UPDATE expenses
                SET user_id = ?
                WHERE user_id IS NULL
            """, (user_id,))

            connection.execute("""
                UPDATE budgets
                SET user_id = ?
                WHERE user_id IS NULL
            """, (user_id,))

            connection.execute("""
                UPDATE planned_expenses
                SET user_id = ?
                WHERE user_id IS NULL
            """, (user_id,))

        connection.commit()
        return user_id

    except sqlite3.IntegrityError:
        connection.rollback()
        return None

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_connection()

    try:
        return connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email.strip().lower(),)).fetchone()

    finally:
        connection.close()


def get_user_by_id(user_id):
    connection = get_connection()

    try:
        return connection.execute("""
            SELECT id, name, email
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

    finally:
        connection.close()


def add_expense_to_db(
    user_id, name, amount, category, expense_date
):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            INSERT INTO expenses
                (user_id, name, amount, category, date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id, name, amount, category, expense_date
        ))

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_all_expenses(user_id):
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT id, name, amount, category, date
            FROM expenses
            WHERE user_id = ?
            ORDER BY id
        """, (user_id,)).fetchall()

        return [
            [
                row["name"],
                row["amount"],
                row["category"],
                row["date"],
                row["id"]
            ]
            for row in rows
        ]

    finally:
        connection.close()


def update_expense_in_db(
    user_id, expense_id, name, amount, category, expense_date
):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            UPDATE expenses
            SET name = ?, amount = ?, category = ?, date = ?
            WHERE id = ? AND user_id = ?
        """, (
            name, amount, category, expense_date,
            expense_id, user_id
        ))

        connection.commit()
        return cursor.rowcount

    finally:
        connection.close()


def delete_expense_from_db(user_id, expense_id):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            DELETE FROM expenses
            WHERE id = ? AND user_id = ?
        """, (expense_id, user_id))

        connection.commit()
        return cursor.rowcount

    finally:
        connection.close()


# Create or update the database schema when this module is imported.
create_table()
