from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os

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

def get_cost_matrix():
    cost_matrix = [[100, 75, 50, 100] for row in range(12)]
    return cost_matrix


def build_seating_chart():
    # Create empty 12x4 chart
    seating_chart = [[{"reserved": False, "name": None} for col in range(4)] for row in range(12)]

    # Load reservations from database
    reservations = Reservation.query.all()

    for r in reservations:
        row = r.seatRow 
        col = r.seatColumn 

        seating_chart[row][col]["reserved"] = True
        seating_chart[row][col]["name"] = r.passengerName

    cost_matrix = get_cost_matrix()
    revenue = sum(cost_matrix[row][col] for row in range(12) for col in range(4) if seating_chart[row][col]["reserved"])

    return seating_chart, revenue, reservations


@app.route("/", methods=["GET", "POST"])
def index():
    # Build seating chart for display on main page
    chart, revenue, reservations = build_seating_chart()

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

    return render_template("index.html", chart=chart)




@app.route("/admin", methods=["GET", "POST"] )
def admin_login():
    #return "<h1>Admin Login Page Placeholder</h1>"
    admin_verified = False
    seating_chart, revenue, reservations = None, 0, []
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        adminUser = Admin.query.filter_by(username=username).first()

        if not username and not password:
            flash("Username and Password Required")
        elif not username:
            flash("Username Required")
        elif not password:
                flash("Password Required")
        elif adminUser and adminUser.password == password:
            flash("Login Sucessful")
            admin_verified = True
            print(admin_verified)
            seating_chart, revenue, reservations = build_seating_chart()
        else:
            flash("Invalid Credentials")
    chart = seating_chart
    return render_template("admin_login.html", admin_verified = admin_verified, seating_chart = seating_chart, chart = chart, revenue = revenue, reservations = reservations, cost_matrix = get_cost_matrix())

@app.route("/admin/delete/<int:res_id>", methods=["POST"])
def delete_reservation(res_id):
    reservation = Reservation.query.get(res_id)
    db.session.delete(reservation)
    db.session.commit()
    flash("Successfully deleted")
    return redirect(url_for("admin_login"))






@app.route("/reserve")
def reserve_seat():
    return "<h1>Seat Reservation Form Placeholder</h1>"


if __name__ == "__main__":
    app.run(debug=True)
