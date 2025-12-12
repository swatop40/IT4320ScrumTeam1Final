from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os
import secrets
from datetime import datetime


app = Flask(__name__)
app.config["SECRET_KEY"] = "devkey"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "reservations.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    passengerName = db.Column(db.String, nullable=False)
    seatRow = db.Column(db.Integer, nullable=False)
    seatColumn = db.Column(db.Integer, nullable=False)
    eTicketNumber = db.Column(db.String, nullable=False)
    created = db.Column(db.String)

class Admin(db.Model):
    __tablename__ = "admins"

    username = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)

# ----- cost matrix -----
def get_cost_matrix():
    cost_matrix = [[100, 75, 50, 100] for _ in range(12)]
    return cost_matrix

COST_MATRIX = get_cost_matrix()
ROWS = 12
COLS = 4

def build_seating_chart():
    # Create empty 12x4 chart
    seating_chart = [[{"reserved": False, "name": None} for _ in range(COLS)] for _ in range(ROWS)]

    # Load reservations from database
    reservations = Reservation.query.all()

    for r in reservations:
        row = int(r.seatRow) - 1   # convert to 0-based index
        col = int(r.seatColumn) - 1

        # Safety check to avoid crashes
        if 0 <= row < ROWS and 0 <= col < COLS:
            seating_chart[row][col]["reserved"] = True
            seating_chart[row][col]["name"] = r.passengerName

    return seating_chart


@app.route("/", methods=["GET", "POST"])
def index():
    # Build seating chart for display on main page
    chart = build_seating_chart()

    if request.method == "POST":
        choice = request.form.get("menu_choice")

        if choice == "option2":
            flash("Redirecting to admin login...")
            return redirect(url_for("admin_login"))

        if choice == "option3":
            flash("Redirecting to reservation form...")
            return redirect(url_for("reserve_seat"))

        flash("Please choose a valid option.")
        return redirect(url_for("index"))

    return render_template("index.html", chart=chart, rows=ROWS, cols=COLS, cost_matrix=COST_MATRIX)



@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.password == password:
            # simple session flag
            session['admin_user'] = admin.username
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if 'admin_user' not in session:
        flash("Please log in as admin to view the dashboard.", "warning")
        return redirect(url_for("admin_login"))

    chart = build_seating_chart()

    # calculate total sales using cost matrix and reservations
    total = 0.0
    reservations = Reservation.query.order_by(Reservation.id.desc()).all()
    for r in reservations:
        rr = int(r.seatRow) - 1
        cc = int(r.seatColumn) - 1
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            total += COST_MATRIX[rr][cc]

    return render_template("admin_dashboard.html", chart=chart, reservations=reservations, total_sales=total)

def generate_eticket(first, last, row, col):
    initials = (first[:1] + last[:1]).upper() if first and last else "XX"
    rand = secrets.token_hex(3).upper()
    return f"{initials}-{row}{col}-{rand}"


def seat_is_taken(row, col):
    existing = Reservation.query.filter_by(seatRow=row, seatColumn=col).first()
    return existing is not None


@app.route("/reserve", methods=["GET", "POST"])
def reserve_seat():
    chart = build_seating_chart()

    if request.method == "POST":
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()

        try:
            row = int(request.form.get("seat_row"))
            col = int(request.form.get("seat_col"))
        except (ValueError, TypeError):
            flash("Row and Column must be numbers.")
            return redirect(url_for("reserve_seat"))

        # validation
        if not first or not last:
            flash("Please provide both first and last name.")
            return redirect(url_for("reserve_seat"))

        if not (1 <= row <= ROWS and 1 <= col <= COLS):
            flash("Selected seat is out of range.")
            return redirect(url_for("reserve_seat"))

        if seat_is_taken(row, col):
            flash(f"Seat R{row}C{col} is already reserved. Choose another seat.")
            return redirect(url_for("reserve_seat"))

        eticket = generate_eticket(first, last, row, col)
        created = datetime.utcnow().isoformat()

        new_res = Reservation(
            passengerName=f"{first} {last}",
            seatRow=row,
            seatColumn=col,
            eTicketNumber=eticket,
            created=created
        )

        db.session.add(new_res)
        db.session.commit()

        return redirect(url_for("confirm_reservation", eticket=eticket))

    return render_template(
        "reserve.html",
        chart=chart,
        rows=ROWS,
        cols=COLS,
        cost_matrix=COST_MATRIX
    )



@app.route("/confirm/<eticket>")
def confirm_reservation(eticket):
    res = Reservation.query.filter_by(eTicketNumber=eticket).first_or_404()
    # compute price from cost matrix
    rr = int(res.seatRow) - 1
    cc = int(res.seatColumn) - 1
    price = COST_MATRIX[rr][cc] if (0 <= rr < ROWS and 0 <= cc < COLS) else 0.0
    return render_template("confirm.html", res=res, price=price)


# ------------- helper route to see total sales (public) -------------
@app.route("/total_sales")
def total_sales_public():
    # compute total sales without admin auth (allowed for demo)
    reservations = Reservation.query.all()
    total = 0.0
    for r in reservations:
        rr = int(r.seatRow) - 1
        cc = int(r.seatColumn) - 1
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            total += COST_MATRIX[rr][cc]
    return f"Total sales (all reservations): ${total:.2f}"




if __name__ == "__main__":
    app.run(debug=True)
