import os
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get data from user db
    userdata = db.execute("SELECT * FROM users WHERE id= :id", id=session["user_id"])

    stocks = db.execute("SELECT symbol, SUM(shares) as total_shares FROM history WHERE id = :id GROUP BY symbol", id=session["user_id"])

    quotes = {}

    # Find an inforamtion about share
    for stock in stocks:
        quotes[stock["symbol"]] = lookup(stock["symbol"])

    # Promt info about cash
    cash_remaining = userdata[0]["cash"]

    total = cash_remaining

    return render_template("index.html", stocks=stocks, quotes=quotes, cash_remaining=cash_remaining, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Ensure that user inputed a symbole
        if not request.form.get("symbol") or len(lookup(request.form.get("symbol"))) == 1:
            return apology ("Invalde symbole")


        # Ensure that user inputed a positive number of shares
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology ("Invalide shares number")

        result = lookup(request.form.get("symbol"))



        if result == None:
            return apology("Invalid Symbole")

        else:

            rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session["user_id"])

            # Amout of shares to buy
            amount = int(request.form.get("shares"))

            cash = rows[0]["cash"]

            # Coast of all shares which user what to buy
            total_price = result["price"] * amount

            # Ensudre that user has enough cash
            if cash < total_price:
                return apology("Not enough cash")

            else:

                # Return current balance after transaction
                current_balance = cash - total_price

                # Make upper
                name = request.form.get("symbol")
                correct = name.upper()

                db.execute("UPDATE users SET cash = :update_cash WHERE id = :user_id",
                update_cash=current_balance, user_id = session["user_id"])

                # Add transaction to history
                db.execute("INSERT INTO history (id, symbol, shares, price) VALUES(:id, :symbol, :shares, :price)",
                    id = session["user_id"],
                    symbol = correct,
                    shares = amount,
                    price = result["price"])

                flash ("Congratulations, you bought shares!")

                return index()
    else:
            return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


@app.route("/history")
@login_required
def history():

    """Show history of transactions"""
    history = db.execute("SELECT * FROM history")
    print(history)
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Ensure if symbole is valid
        if len(request.form.get("symbol")) == 1:
            return apology("Invalid Symbole")

        # Make a json request
        result = lookup(request.form.get("symbol"))

        # Validate a respond
        if result == None:
            return apology("Invalid Symbole")

        # Render a template
        return render_template("quote.html", mode="post",
        name=result["name"], symbol=result["symbol"], price=result["price"])

    else:
        return render_template("quote.html", mode="get")


    #return render_template("quote.html", mode="get")

# Process of vaditation data and registration
@app.route("/register", methods=["GET", "POST"])
def registration():

    session.clear()

    if request.method == "POST":

            """Register user"""
            # Ensure that user data inserted correct
            if not request.form.get("username"):
                return apology("username not correct")

                # Ensure that password data inserted correct
            elif not request.form.get("password") == request.form.get("password_confirm"):
                return apology("password doesn't match")

            # Add to the DB
            result = db.execute("SELECT * FROM users WHERE username = :username",
                        username = request.form.get("username"))

            # Ensure where username is free
            if len(result) == 1:
                return apology("username is not free")

            else:
                db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))

                rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

                # Remember which user has logged in
                session["user_id"] = rows[0]["id"]

                # Redirect user to home page
                return render_template("index.html")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":

        # Ensure that user inputed number of stocks
        if not request.form.get('shares'):
            return apology("Funny, but input more stocks")
        elif request.form.get('shares') == '0':
            return apology("0 shares, it's look like you are the billionaire")
        elif not request.form.get('symbol'):
            return apology("Select a sybmol")

        # Ensure in value positive
        try:
            amount = int(request.form.get('shares'))
        except:
            return apology("Invalide value")

        # Write a data from webpage
        amount = int(request.form.get('shares'))
        name = request.form.get('symbol')

        # Chech current status of shares
        current = db.execute("SELECT symbol, SUM(shares) as suma FROM history WHERE symbol LIKE :symbol", symbol=name)

        # Validate whether user has enough shares
        if int(current[0]["suma"]) < amount:
            return apology("Not enough shares")
        else:

            # Check current price of share
            current_price = lookup(request.form.get("symbol"))

            # Calculate total price of sold shares
            earned_cash = (current_price['price']) * amount
            statement = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])

            # Calculate great cash
            cash = statement[0]["cash"] + earned_cash

            # Add info to the history
            db.execute("INSERT INTO history (id, symbol, shares, price) VALUES (:id, :symbol, :shares, :price)",
                    id = session["user_id"],
                    symbol = request.form.get("symbol"),
                    shares = -amount,
                    price = earned_cash)
            # Update cash info
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id=session["user_id"])

            flash ("Congratulations, you've sold shares!")

            return redirect("/")

            #UPDATE "users" SET "id"='4', "username"='Alex',
            #"hash"='pbkdf2:sha256:50000$Eb3FJOnS$6b1ae56d48be4b642dce0fb91840b8d48b97bcbfbb2660587007d68058d8f944',
            #"cash"='1000' WHERE "rowid" = 4


            #INSERT INTO history (id, symbol, shares, price) VALUES(:id, :symbol, :shares, :price
    else:

        shares = db.execute("SELECT symbol FROM history")

        names = []

        for share in shares:
            names.append(share['symbol'])

        # make a set of uniqe values
        mset = set(names)
        names = list(mset)
        names.sort()

        return render_template("sell.html", names=names, mode='get')

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
