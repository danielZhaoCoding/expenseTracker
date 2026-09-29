from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "dev-secret-key"

DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            expense_date TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    categories = [
        ("Food",),
        ("Transport",),
        ("Entertainment",),
        ("Shopping",),
        ("Bills",),
        ("Other",)
    ]

    conn.executemany(
        "INSERT OR IGNORE INTO categories (name) VALUES (?)",
        categories
    )

    conn.commit()
    conn.close()


@app.route("/")
def dashboard():
    conn = get_db()

    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses"
    ).fetchone()["total"]

    count = conn.execute(
        "SELECT COUNT(*) AS count FROM expenses"
    ).fetchone()["count"]

    recent = conn.execute("""
        SELECT
            expenses.*,
            categories.name AS category
        FROM expenses
        JOIN categories ON expenses.category_id = categories.id
        ORDER BY expense_date DESC, expenses.id DESC
        LIMIT 5
    """).fetchall()

    by_category = conn.execute("""
        SELECT
            categories.name AS category,
            COALESCE(SUM(expenses.amount), 0) AS total
        FROM categories
        LEFT JOIN expenses
            ON expenses.category_id = categories.id
        GROUP BY categories.id
        ORDER BY total DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        count=count,
        recent=recent,
        by_category=by_category
    )


@app.route("/expenses")
def expenses():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            expenses.*,
            categories.name AS category
        FROM expenses
        JOIN categories ON expenses.category_id = categories.id
        ORDER BY expense_date DESC, expenses.id DESC
    """).fetchall()

    conn.close()

    return render_template("expenses.html", expenses=rows)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    conn = get_db()

    categories = conn.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()

    if request.method == "POST":
        amount = request.form["amount"]
        category_id = request.form["category_id"]
        description = request.form["description"]
        expense_date = request.form["expense_date"]

        if not amount or not category_id or not expense_date:
            flash("Please fill in all required fields.", "error")
            conn.close()
            return render_template(
                "add_expense.html",
                categories=categories
            )

        conn.execute("""
            INSERT INTO expenses
            (amount, category_id, description, expense_date)
            VALUES (?, ?, ?, ?)
        """, (
            float(amount),
            category_id,
            description,
            expense_date
        ))

        conn.commit()
        conn.close()

        flash("Expense added!", "success")
        return redirect(url_for("expenses"))

    conn.close()

    return render_template(
        "add_expense.html",
        categories=categories,
        today=date.today().isoformat()
    )


@app.route("/expenses/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()
    conn.close()

    flash("Expense deleted.", "success")
    return redirect(url_for("expenses"))


@app.route("/categories", methods=["GET", "POST"])
def categories():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()

        if name:
            try:
                conn.execute(
                    "INSERT INTO categories (name) VALUES (?)",
                    (name,)
                )
                conn.commit()
                flash("Category added!", "success")
            except sqlite3.IntegrityError:
                flash("That category already exists.", "error")

    rows = conn.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()

    conn.close()

    return render_template(
        "categories.html",
        categories=rows
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)