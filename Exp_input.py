
from datetime import datetime
from db import (
    add_expense_to_db,
    get_all_expenses,
    update_expense_in_db,
    delete_expense_from_db
)

def get_yes_no(prompt):
    while True:
        answer = input(prompt).strip().lower()

        if answer in ("yes", "no"):
            return answer

        print("Please enter yes or no.")


def get_valid_date():
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]

    while True:
        date_text = input("Enter date: ").strip()

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_text, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue

        print("Invalid date! Please try again.")


def amount_valid():
    while True:
        try:
            amount = float(input("Enter Amount: "))

            if amount <= 0:
                print("Amount must be greater than zero.")
                continue

            return amount

        except ValueError:
            print("Invalid input! Please enter a valid amount.")


def get_valid_number(prompt):
    while True:
        try:
            number = int(input(prompt))
            return number

        except ValueError:
            print("Invalid input! Please enter a whole number.")


def get_valid_name():
    while True:
        name = input("Enter expense name: ").strip()

        if name:
            return name

        print("Expense name cannot be empty.")


def get_valid_category():
    while True:
        category = input("Enter expense category: ").strip()

        if category:
            return category

        print("Category cannot be empty.")


def display_expenses(Expense):
    if not Expense:
        print("No expenses available.")
        return

    print("\n========== EXPENSE REPORT ==========")

    for number, expense in enumerate(Expense, start=1):
        print(
            number,
            "| Expense =", expense[0],
            "| Amount = ₹", expense[1],
            "| Category =", expense[2],
            "| Date =", expense[3]
        )


def search_by_category(Expense):
    if not Expense:
        print("No expenses available to search.")
        return

    search_category = input(
        "Enter category to search: "
    ).strip().casefold()

    found = False

    for expense in Expense:
        if expense[2].casefold() == search_category:
            print(
                "Expense:", expense[0],
                "| Amount: ₹", expense[1],
                "| Date:", expense[3]
            )
            found = True

    if not found:
        print("No expenses found in this category.")


def sort_expenses(Expense):
    sorted_list = sorted(
        Expense,
        key=lambda expense: expense[1],
        reverse=True
    )

    print("\nExpenses from highest to lowest:")

    for expense in sorted_list:
        print(
            expense[0],
            "| ₹", expense[1],
            "|", expense[2],
            "|", expense[3]
        )


def filter_by_date(Expense):
    while True:
        print("Enter start date:")
        start_date = get_valid_date()

        print("Enter end date:")
        end_date = get_valid_date()

        if start_date <= end_date:
            break

        print("Start date cannot be after end date. Try again.")

    found = False

    print("\nExpenses within the selected date range:")

    for expense in Expense:
        if start_date <= expense[3] <= end_date:
            print(
                expense[0],
                "| ₹", expense[1],
                "|", expense[2],
                "|", expense[3]
            )
            found = True

    if not found:
        print("No expenses found in this date range.")



def delete_expense(Expense):
    if not Expense:
        print("No expenses available to delete.")
        return

    display_expenses(Expense)

    delete_no = get_valid_number(
        "Enter expense number to delete: "
    )

    if delete_no < 1 or delete_no > len(Expense):
        print("Invalid expense number. No expense deleted.")
        return

    expense = Expense[delete_no - 1]
    expense_id = expense[4]

    deleted = delete_expense_from_db(expense_id)

    if deleted:
        Expense.pop(delete_no - 1)
        print("Deleted expense:", expense[0])
    else:
        print("Expense was not found in the database.")



def edit_expense(Expense):
    if not Expense:
        print("No expenses available to edit.")
        return

    display_expenses(Expense)

    edit_no = get_valid_number(
        "Enter expense number to edit: "
    )

    if edit_no < 1 or edit_no > len(Expense):
        print("Invalid expense number. No expense edited.")
        return

    print("\nWhat would you like to edit?")
    print("1. Expense name")
    print("2. Amount")
    print("3. Category")
    print("4. Date")
    print("5. Cancel")

    while True:
        choice = get_valid_number("Choose field (1-5): ")

        if 1 <= choice <= 5:
            break

        print("Invalid choice. Enter a number from 1 to 5.")

    expense = Expense[edit_no - 1]

    if choice == 1:
        expense[0] = get_valid_name()
    elif choice == 2:
        expense[1] = amount_valid()
    elif choice == 3:
        expense[2] = get_valid_category()
    elif choice == 4:
        expense[3] = get_valid_date()
    elif choice == 5:
        print("Editing canceled.")
        return

    expense_id = expense[4]

    updated = update_expense_in_db(
        expense_id,
        expense[0],
        expense[1],
        expense[2],
        expense[3]
    )

    if updated:
        print("Expense updated successfully.")
    else:
        print("Expense was not found in the database.")


def show_summary(Expense):
    total = sum(expense[1] for expense in Expense)

    print("\n========== FINAL SUMMARY ==========")
    print("Total number of expenses:", len(Expense))
    print("Total expense: ₹", round(total, 2))

    if not Expense:
        print("No expenses available for further calculations.")
        return total

    average = total / len(Expense)
    print("Average expense: ₹", round(average, 2))

    highest_amount = max(expense[1] for expense in Expense)

    print("\nHighest expense(s):")

    for expense in Expense:
        if expense[1] == highest_amount:
            print(expense[0], "| Amount: ₹", expense[1])

    category_totals = {}

    for expense in Expense:
        category = expense[2].strip().casefold()
        category_totals[category] = (
            category_totals.get(category, 0) + expense[1]
        )

    print("\nTotal expense by category:")

    for category, amount in category_totals.items():
        print(category.title(), ": ₹", round(amount, 2))

    monthly_expense = {}

    for expense in Expense:
        date_obj = datetime.strptime(expense[3], "%Y-%m-%d")
        month_year = date_obj.strftime("%B %Y")

        monthly_expense[month_year] = (
            monthly_expense.get(month_year, 0) + expense[1]
        )

    print("\nTotal expense by month:")

    for month_year, amount in sorted(monthly_expense.items()):
        print(month_year, ": ₹", round(amount, 2))

    return total


def add_expense():
    Expense = get_all_expenses()

    print("========== ADD EXPENSE ==========")

    while True:
        expense = [
            get_valid_name(),
            amount_valid(),
            get_valid_category(),
            get_valid_date()
        ]

        expense_id = add_expense_to_db(*expense)
        expense.append(expense_id)
        Expense.append(expense)

        print("Expense added successfully.")

        if get_yes_no(
            "Do you want to add another expense? (yes/no): "
        ) == "no":
            break

    display_expenses(Expense)

    if get_yes_no(
        "Do you want to search by category? (yes/no): "
    ) == "yes":
        search_by_category(Expense)

    if get_yes_no(
        "Do you want to sort expenses by amount? (yes/no): "
    ) == "yes":
        if Expense:
            sort_expenses(Expense)
        else:
            print("No expenses available to sort.")

    if get_yes_no(
        "Do you want to filter expenses by date range? (yes/no): "
    ) == "yes":
        if Expense:
            filter_by_date(Expense)
        else:
            print("No expenses available to filter.")

    if get_yes_no(
        "Do you want to delete an expense? (yes/no): "
    ) == "yes":
        delete_expense(Expense)

    if get_yes_no(
        "Do you want to edit an expense? (yes/no): "
    ) == "yes":
        edit_expense(Expense)

    display_expenses(Expense)

    return show_summary(Expense)


print("Final total: ₹", round(add_expense(), 2))
