from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from db import (
    add_expense_to_db,
    get_all_expenses,
    update_expense_in_db,
    delete_expense_from_db
)
from datetime import date
from collections import defaultdict
import sqlite3
import math

app = Flask(__name__)
app.secret_key = "spend-story-local-secret-key"

DATABASE = "expenses.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_extra_tables():
    """Create budget and planner tables without changing expense records."""
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                month_key TEXT PRIMARY KEY,
                amount REAL NOT NULL CHECK(amount > 0)
            )
        """)

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
        connection.commit()
    finally:
        connection.close()


create_extra_tables()


def validate_expense_form():
    name = request.form.get("name", "").strip()
    amount_text = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    expense_date = request.form.get("date", "").strip()

    if not all([name, amount_text, category, expense_date]):
        return None, "Please fill in all expense fields."

    try:
        amount = float(amount_text)
        if not math.isfinite(amount) or amount <= 0:
            return None, "Amount must be greater than zero."
    except ValueError:
        return None, "Please enter a valid amount."

    try:
        date.fromisoformat(expense_date)
    except ValueError:
        return None, "Please enter a valid date."

    return (name, amount, category, expense_date), None


def validate_plan_form():
    name = request.form.get("plan_name", "").strip()
    amount_text = request.form.get("plan_amount", "").strip()
    category = request.form.get("plan_category", "").strip()
    planned_date = request.form.get("plan_date", "").strip()
    notes = request.form.get("plan_notes", "").strip()

    if not all([name, amount_text, category, planned_date]):
        return None, "Please fill in all required planner fields."

    try:
        amount = float(amount_text)
        if not math.isfinite(amount) or amount <= 0:
            return None, "Planned amount must be greater than zero."
    except ValueError:
        return None, "Please enter a valid planned amount."

    try:
        parsed_date = date.fromisoformat(planned_date)
        if parsed_date < date.today():
            return None, "Please choose today or a future date."
    except ValueError:
        return None, "Please enter a valid planned date."

    return (name, amount, category, planned_date, notes), None


@app.route("/")
def home():
    expenses = get_all_expenses()
    today = date.today()
    current_month = today.strftime("%Y-%m")

    total_expenses = sum(float(e[1]) for e in expenses)
    transaction_count = len(expenses)

    monthly_expenses = sum(
        float(e[1]) for e in expenses
        if str(e[3]).startswith(current_month)
    )

    expense_days = {
        str(e[3]) for e in expenses
        if str(e[3]).startswith(current_month)
    }
    daily_average = (
        monthly_expenses / len(expense_days)
        if expense_days else 0
    )

    # Category totals
    category_totals = defaultdict(float)
    for expense in expenses:
        category_totals[str(expense[2]).strip()] += float(expense[1])

    category_data = []
    palette = [
        "#69b9a5", "#8aa9d6", "#f0b48e",
        "#d99bb5", "#b4a0d5", "#e3c66d",
        "#82b9c9", "#a4b98a"
    ]

    for index, (category, amount) in enumerate(
        sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ):
        percentage = (
            amount / total_expenses * 100
            if total_expenses else 0
        )
        category_data.append({
            "name": category,
            "amount": amount,
            "percentage": percentage,
            "color": palette[index % len(palette)]
        })

    # Monthly chart for current year
    monthly_totals = defaultdict(float)
    for expense in expenses:
        expense_date = str(expense[3])
        if len(expense_date) >= 7 and expense_date[:4] == str(today.year):
            monthly_totals[expense_date[:7]] += float(expense[1])

    monthly_labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    monthly_values = [
        monthly_totals.get(f"{today.year}-{month:02d}", 0)
        for month in range(1, 13)
    ]

    # Filter options
    filter_categories = sorted({
        str(e[2]).strip() for e in expenses
        if str(e[2]).strip()
    })

    month_keys = sorted({
        str(e[3])[:7] for e in expenses
        if len(str(e[3])) >= 7
    }, reverse=True)

    available_months = []
    for month_key in month_keys:
        try:
            month_label = date.fromisoformat(
                month_key + "-01"
            ).strftime("%B %Y")
            available_months.append((month_key, month_label))
        except ValueError:
            pass

    # Quick insight
    if category_totals:
        highest_category = max(category_totals, key=category_totals.get)
        highest_amount = category_totals[highest_category]
        insight_title = f"{highest_category} is your top spending category"
        insight_message = (
            f"You have spent ₹{highest_amount:.2f} on "
            f"{highest_category} so far."
        )
    else:
        insight_title = "Your story is just beginning!"
        insight_message = "Add your first expense to discover your spending habits."

    # Monthly budget
    connection = get_connection()
    try:
        budget_row = connection.execute(
            "SELECT amount FROM budgets WHERE month_key = ?",
            (current_month,)
        ).fetchone()

        plan_rows = connection.execute("""
            SELECT id, name, amount, category, planned_date, notes
            FROM planned_expenses
            WHERE planned_date >= ?
            ORDER BY planned_date ASC
        """, (today.isoformat(),)).fetchall()
    finally:
        connection.close()

    budget_amount = float(budget_row["amount"]) if budget_row else 0
    budget_remaining = max(budget_amount - monthly_expenses, 0)
    budget_over = max(monthly_expenses - budget_amount, 0) if budget_amount else 0

    budget_progress = (
        min(monthly_expenses / budget_amount * 100, 100)
        if budget_amount else 0
    )

    # Planner totals
    planned_expenses = [dict(row) for row in plan_rows]
    planned_total = sum(float(row["amount"]) for row in planned_expenses)

    planned_month_total = sum(
        float(row["amount"]) for row in planned_expenses
        if str(row["planned_date"]).startswith(current_month)
    )

    projected_month_spending = monthly_expenses + planned_month_total
    projected_over_budget = (
        max(projected_month_spending - budget_amount, 0)
        if budget_amount else 0
    )

    return render_template(
        "home.html",
        expenses=expenses,
        total_expenses=total_expenses,
        monthly_expenses=monthly_expenses,
        transaction_count=transaction_count,
        daily_average=daily_average,
        category_data=category_data,
        monthly_labels=monthly_labels,
        monthly_values=monthly_values,
        current_year=today.year,
        current_month=current_month,
        current_month_label=today.strftime("%B %Y"),
        filter_categories=filter_categories,
        available_months=available_months,
        insight_title=insight_title,
        insight_message=insight_message,
        budget_amount=budget_amount,
        budget_remaining=budget_remaining,
        budget_over=budget_over,
        budget_progress=budget_progress,
        planned_expenses=planned_expenses,
        planned_total=planned_total,
        planned_month_total=planned_month_total,
        projected_month_spending=projected_month_spending,
        projected_over_budget=projected_over_budget,
        today=today.isoformat()
    )


@app.route("/add", methods=["POST"])
def add_expense():
    expense, error = validate_expense_form()
    if error:
        flash(error, "error")
        return redirect(url_for("home") + "#expense-form")

    name, amount, category, expense_date = expense
    add_expense_to_db(name, amount, category, expense_date)
    flash("Expense added successfully!", "success")
    return redirect(url_for("home") + "#transactions")


@app.route("/edit/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):
    expense, error = validate_expense_form()
    if error:
        flash(error, "error")
        return redirect(url_for("home") + "#transactions")

    name, amount, category, expense_date = expense
    updated_rows = update_expense_in_db(
        expense_id, name, amount, category, expense_date
    )

    if updated_rows == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense updated successfully!", "success")

    return redirect(url_for("home") + "#transactions")


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    deleted_rows = delete_expense_from_db(expense_id)

    if deleted_rows == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense deleted.", "success")

    return redirect(url_for("home") + "#transactions")


@app.route("/budget", methods=["POST"])
def save_budget():
    amount_text = request.form.get("budget_amount", "").strip()
    month_key = date.today().strftime("%Y-%m")

    try:
        amount = float(amount_text)
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid budget amount greater than zero.", "error")
        return redirect(url_for("home") + "#goals")

    connection = get_connection()
    try:
        connection.execute("""
            INSERT INTO budgets (month_key, amount)
            VALUES (?, ?)
            ON CONFLICT(month_key)
            DO UPDATE SET amount = excluded.amount
        """, (month_key, amount))
        connection.commit()
    finally:
        connection.close()

    flash("Monthly budget saved!", "success")
    return redirect(url_for("home") + "#goals")


@app.route("/plan", methods=["POST"])
def add_plan():
    plan, error = validate_plan_form()
    if error:
        flash(error, "error")
        return redirect(url_for("home") + "#planner")

    name, amount, category, planned_date, notes = plan

    connection = get_connection()
    try:
        connection.execute("""
            INSERT INTO planned_expenses
            (name, amount, category, planned_date, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (name, amount, category, planned_date, notes))
        connection.commit()
    finally:
        connection.close()

    flash("Planned expense added!", "success")
    return redirect(url_for("home") + "#planner")


@app.route("/plan/delete/<int:plan_id>", methods=["POST"])
def delete_plan(plan_id):
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM planned_expenses WHERE id = ?",
            (plan_id,)
        )
        connection.commit()
        deleted_rows = cursor.rowcount
    finally:
        connection.close()

    if deleted_rows:
        flash("Planned expense removed.", "success")
    else:
        flash("Planned expense not found.", "error")

    return redirect(url_for("home") + "#planner")


if __name__ == "__main__":
    app.run()