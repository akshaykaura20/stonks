import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

from datetime import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# A db connection function
def setup_connection():
    connection = sqlite3.connect("stockQuote.db", isolation_level=None)
    connection.row_factory = sqlite3.Row 
    return connection.cursor()

# Make sure API key is set



@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    c = setup_connection()

    c.execute("SELECT username, cash FROM users WHERE id = ?", (session["user_id"], ))
    current_user = c.fetchall()

    c.execute('''SELECT symbol, SUM(shares)
                            FROM all_transactions WHERE name = ? GROUP BY symbol''',
                            (current_user[0]['username'], ))
    sym_shares = c.fetchall()               
    count = len(sym_shares)

    current_cash =  current_user[0]['cash']
    current_prices = []

    gtotal = 0.00
    for i in range(count):
        look = lookup(sym_shares[i]['symbol'])
        current_prices.append(look['price'])
        t = sym_shares[i]['SUM(shares)'] * current_prices[i]
        gtotal += t

    gtotal += current_user[0]['cash']
    return render_template("index.html", sym_shares=sym_shares, current_cash=current_cash, current_prices=current_prices, count=count, gtotal=gtotal)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    c = setup_connection()

    if request.method == "POST":
        if lookup(request.form.get("symbol")) == None:
            flash("No such stock.", category="error")
            return redirect("/buy")
        elif int(request.form.get("shares")) <= 0:
            flash("Enter a positive number of stocks.", category="error")
            return redirect("/buy")
        else:
            rows = lookup(request.form.get("symbol"))
            cash_required = float(rows["price"] * int(request.form.get("shares")))
            cash_required = round(cash_required, 2)

            c.execute("SELECT * FROM users WHERE id = ?", (session["user_id"], ))
            rows1 = c.fetchall()
            user_cash = float(rows1[0]["cash"])
            user_cash = round(user_cash, 2)

            if cash_required > user_cash:
                flash("Insufficient cash.", category="error")
                return redirect("/buy")
            else:
                c.execute('''UPDATE users SET cash = ?
                                WHERE username = ?''', (user_cash - cash_required, rows1[0]['username']))
                c.execute('''INSERT INTO all_transactions
                            VALUES(?, ?, ?, ?, ?)''',
                            (rows1[0]['username'], datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                             request.form.get("symbol"), int(request.form.get("shares")), rows["price"]))
            flash("Bought stock successfully.", category="message")
            return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    c = setup_connection()

    c.execute("SELECT username, cash FROM users WHERE id = ?", (session["user_id"], ))
    current_user = c.fetchall()

    c.execute('''SELECT dnt, symbol, shares, price
                            FROM all_transactions WHERE name = ?''',
                            (current_user[0]['username'], ))
    transactions = c.fetchall()
    count = len(transactions)

    return render_template("history.html", current_user=current_user, transactions=transactions, count=count)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    c = setup_connection()

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide a username.", category="error")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide password.", category="error")
            return redirect("/login")

        # Query database for username
        c.execute("SELECT * FROM users WHERE username = ?",
                          (request.form.get("username"), ))
        user_rows = c.fetchall()

        # Ensure username exists and password is correct
        if len(user_rows) != 1 or not check_password_hash(user_rows[0]["hash"], request.form.get("password")):
            flash("Inavlid username and/or password.", category="error")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = user_rows[0]["id"]

        # Redirect user to home page
        flash("Logged In.", category="message")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()
    flash("Logged out successfully", category="message")
    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        if lookup(request.form.get("symbol")) == None:
            flash("No such stock.", category="error")
            return redirect("/quote")
        else:
            rows = lookup(request.form.get("symbol"))
            return render_template("quoted.html", rows = rows)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User submitted to register.html via POST request method
    if request.method == "POST":
        c = setup_connection()
        # Check for blank input fields
        if not request.form.get("username"):
            flash("Must provide a username.", category="error")
            return redirect("/register")
        elif not request.form.get("password"):
            flash("Must set a password.", category="error")
            return redirect("/register")
        elif not request.form.get("confirmation"):
            flash("Must confirm password.", category="error")
            return redirect("/register")

        # Query for the entered username if already exists in db
        c.execute("SELECT * FROM users WHERE username = ?",
                          (request.form.get("username"), ))
        
        rows = c.fetchall()
        if len(rows) != 0:
            flash("Username already exists.", category="error")
            return redirect("/register")
        # Entered password field and confirmation field must match exactly
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords don't match.", category="error")
            return redirect("/register")
        # If all good then add the user to db
        else:
            c.execute('''INSERT INTO users (username, hash)
                        VALUES (?, ?)''', (request.form.get("username"),
                        generate_password_hash(request.form.get("password"))))

        # Redirect user to login with credentials just entered
        flash("Registered successfully.", category="message")
        return redirect("/login")

    # If not POST request then must be GET, hence just take to registration page
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    c = setup_connection()

    c.execute("SELECT username, cash FROM users WHERE id = ?", (session["user_id"], ))
    current_user = c.fetchall()

    c.execute('''SELECT symbol, SUM(shares)
                            FROM all_transactions WHERE name = ? GROUP BY symbol''',
                            (current_user[0]['username'], ))
    sym_shares = c.fetchall()
    count = len(sym_shares)

    if request.method == "POST":
        f = 0
        for i in range(count):
            if sym_shares[i]["symbol"] == request.form.get("symbol"):
                f = i
                break
        if not request.form.get("symbol"):
            flash("Please select a symbol.", category="message")
            return redirect("/sell")
        elif int(request.form.get("shares")) <= 0 :
            flash("Enter a positive number of shares.", category="message")
            return redirect("/sell")

        elif int(request.form.get("shares")) > sym_shares[f]["SUM(shares)"]:
            flash("You don't have that many of them.", category="message")
            return redirect("/sell")
        else:
            rows = lookup(request.form.get("symbol"))
            selling_total = float(rows["price"] * int(request.form.get("shares")))
            selling_total = round(selling_total, 2)

            c.execute('''UPDATE users SET cash = ?
                        WHERE username = ?''', (current_user[0]['cash'] + selling_total, current_user[0]['username']))
            c.execute('''INSERT INTO all_transactions
                        VALUES(?, ?, ?, ?, ?)''',
                        (current_user[0]['username'], datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                         request.form.get("symbol"), - int(request.form.get("shares")), rows["price"]))

            flash("Sold stock successfully.", category="message")
            return redirect("/")

    else:
        return render_template("sell.html", sym_shares=sym_shares, count=count)


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Add more cash"""
    c = setup_connection()

    if request.method == "POST":
        c.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"], ))
        current_cash = c.fetchall()
        c.execute('''UPDATE users SET cash = ? WHERE id = ?''',
                    (current_cash[0]['cash'] + float(request.form.get("addcash")), session["user_id"]))
        flash("Added cash successfully.", category="message")
        return redirect("/")
    else:
        return render_template("add_cash.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
      app.run(host="0.0.0.0", port=80, debug=True)