from flask import Flask, render_template, url_for, redirect, request, session
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "shinxity"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shinxity.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = 'shinxity'

app.permanent_session_lifetime = timedelta(days=5)

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __init__(self, full_name, username, password_hash):
        self.full_name = full_name
        self.username = username
        self.password_hash = password_hash


@app.route("/", methods = ["GET", "POST"])
@app.route("/login", methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        possible_password = request.form["password"]
        found_user = User.query.filter_by(username=user).first()
        if (found_user and check_password_hash(found_user.password_hash, possible_password)):
            session.permanent = True
            session["username"] = user
        else:
            # flash message saying invalid username / password
            pass
        return redirect(url_for("home"))
    else:
        if "username" in session:
            return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    if request.method == "POST":
        session.permanent = True
        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        found_user = User.query.filter_by(username = username).first()
        if found_user:
            session["username"] = found_user.username
        else:
            hashed = generate_password_hash(password)
            user = User(name, username, hashed)
            db.session.add(user)
            db.session.commit()
            session["username"] = username
        return redirect(url_for("home"))
    else:
        if "username" in session:
            return redirect(url_for("home"))
    return render_template("register.html")

@app.route("/home", methods = ["GET", "POST"])
def home():
    if "username" in session:
        username = session["username"]
        return render_template("home.html", username = username)
    else:
        return redirect(url_for("login"))

@app.route("/logout", methods = ["POST"])
def logout():
    if "username" in session:
        session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(port=8000, debug=True)
