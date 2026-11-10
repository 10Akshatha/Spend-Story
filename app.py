
import os
import math
import secrets
import sqlite3

from datetime import date
from collections import defaultdict
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, abort, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

from db import (
    get_connection,
    create_user,
    get_user_by_email,
    get_user_by_id,
    add_expense_to_db,
    get_all_expenses,
    update_expense_in_db,
    delete_expense_from_db
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("Set the SECRET_KEY environment variable before running the app.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    SESSION_COOKIE_SAMESITE="Lax"
)



def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id or get_user_by_id(user_id) is None:
            session.clear()
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view



@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get("csrf_token")
        submitted = request.form.get("csrf_token")
        if not token or not submitted or not secrets.compare_digest(token, submitted):
            abort(400, description="Invalid form security token. Refresh and try again.")


@app.context_processor
def inject_template_values():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    user = None
    if session.get("user_id"):
        user = get_user_by_id(session["user_id"])

    return {
        "csrf_token": session["csrf_token"],
        "current_user": user
    }


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
        return None, "Please enter a valid amount."

    try:
        parsed_date = date.fromisoformat(planned_date)
        if parsed_date < date.today():
            return None, "Please choose today or a future date."
    except ValueError:
        return None, "Please enter a valid planned date."

    return (name, amount, category, planned_date, notes), None


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please complete all fields.", "error")
            return redirect(url_for("register"))

        if len(name) > 80 or len(email) > 254:
            flash("Please check the length of your details.", "error")
            return redirect(url_for("register"))

        if len(password) < 10:
            flash("Password must contain at least 10 characters.", "error")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        try:
            user_id = create_user(name, email, password_hash)
        except sqlite3.IntegrityError:
            user_id = None

        if user_id is None:
            flash("An account with that email may already exist.", "error")
            return redirect(url_for("register"))

        session.clear()
        session["user_id"] = user_id
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash("Your account has been created!", "success")
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash("Welcome back!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/service-worker.js")
def service_worker():
    return send_from_directory(
        "static",
        "service-worker.js",
        mimetype="application/javascript"
    )


@app.route("/")
@login_required
def home():
    user_id = session["user_id"]
    expenses = get_all_expenses(user_id)
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
    daily_average = monthly_expenses / len(expense_days) if expense_days else 0

    category_totals = defaultdict(float)
    for expense in expenses:
        category_totals[str(expense[2]).strip()] += float(expense[1])

    palette = [
        "#69b9a5", "#8aa9d6", "#f0b48e",
        "#d99bb5", "#b4a0d5", "#e3c66d",
        "#82b9c9", "#a4b98a"
    ]

    category_data = []
    for index, (category, amount) in enumerate(
        sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ):
        percentage = amount / total_expenses * 100 if total_expenses else 0
        category_data.append({
            "name": category,
            "amount": amount,
            "percentage": percentage,
            "color": palette[index % len(palette)]
        })

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

    filter_categories = sorted({
        str(e[2]).strip() for e in expenses if str(e[2]).strip()
    })

    month_keys = sorted({
        str(e[3])[:7] for e in expenses if len(str(e[3])) >= 7
    }, reverse=True)

    available_months = []
    for month_key in month_keys:
        try:
            label = date.fromisoformat(month_key + "-01").strftime("%B %Y")
            available_months.append((month_key, label))
        except ValueError:
            pass

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

    connection = get_connection()
    try:
        budget_row = connection.execute("""
            SELECT amount FROM budgets
            WHERE month_key = ? AND user_id = ?
        """, (current_month, user_id)).fetchone()

        plan_rows = connection.execute("""
            SELECT id, name, amount, category, planned_date, notes
            FROM planned_expenses
            WHERE user_id = ? AND planned_date >= ?
            ORDER BY planned_date ASC
        """, (user_id, today.isoformat())).fetchall()
    finally:
        connection.close()

    budget_amount = float(budget_row["amount"]) if budget_row else 0
    budget_remaining = max(budget_amount - monthly_expenses, 0)
    budget_over = max(monthly_expenses - budget_amount, 0) if budget_amount else 0
    budget_progress = (
        min(monthly_expenses / budget_amount * 100, 100)
        if budget_amount else 0
    )

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
@login_required
def add_expense():
    expense, error = validate_expense_form()
    if error:
        flash(error, "error")
        return redirect(url_for("home") + "#expense-form")

    name, amount, category, expense_date = expense
    add_expense_to_db(
        session["user_id"], name, amount, category, expense_date
    )
    flash("Expense added successfully!", "success")
    return redirect(url_for("home") + "#transactions")


@app.route("/edit/<int:expense_id>", methods=["POST"])
@login_required
def edit_expense(expense_id):
    expense, error = validate_expense_form()
    if error:
        flash(error, "error")
        return redirect(url_for("home") + "#transactions")

    name, amount, category, expense_date = expense
    updated = update_expense_in_db(
        session["user_id"], expense_id,
        name, amount, category, expense_date
    )

    flash(
        "Expense updated successfully!" if updated else "Expense not found.",
        "success" if updated else "error"
    )
    return redirect(url_for("home") + "#transactions")


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    deleted = delete_expense_from_db(session["user_id"], expense_id)
    flash(
        "Expense deleted." if deleted else "Expense not found.",
        "success" if deleted else "error"
    )
    return redirect(url_for("home") + "#transactions")


@app.route("/budget", methods=["POST"])
@login_required
def save_budget():
    try:
        amount = float(request.form.get("budget_amount", "").strip())
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid budget amount greater than zero.", "error")
        return redirect(url_for("home") + "#goals")

    month_key = date.today().strftime("%Y-%m")
    connection = get_connection()
    try:
        connection.execute("""
            INSERT INTO budgets (user_id, month_key, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, month_key)
            DO UPDATE SET amount = excluded.amount
        """, (session["user_id"], month_key, amount))
        connection.commit()
    finally:
        connection.close()

    flash("Monthly budget saved!", "success")
    return redirect(url_for("home") + "#goals")


@app.route("/plan", methods=["POST"])
@login_required
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
            (user_id, name, amount, category, planned_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], name, amount,
            category, planned_date, notes
        ))
        connection.commit()
    finally:
        connection.close()

    flash("Planned expense added!", "success")
    return redirect(url_for("home") + "#planner")


@app.route("/plan/delete/<int:plan_id>", methods=["POST"])
@login_required
def delete_plan(plan_id):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            DELETE FROM planned_expenses
            WHERE id = ? AND user_id = ?
        """, (plan_id, session["user_id"]))
        connection.commit()
        deleted = cursor.rowcount
    finally:
        connection.close()

    flash(
        "Planned expense removed." if deleted else "Planned expense not found.",
        "success" if deleted else "error"
    )
    return redirect(url_for("home") + "#planner")

if __name__ == "__main__":
    app.run()
