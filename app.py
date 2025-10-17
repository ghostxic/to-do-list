from flask import Flask, render_template, url_for, redirect, request, session
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "shinxity"
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://users.sqlite3"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(days=5)

# db = SQLAlchemy(app)

# class users(db.Model):
#     _id = db.Column("id", db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     username = db.Column(db.String(100))
#     password = db.Column(db.String(100))

#     def __init__(self, name, username, password):
#         self.name = name
#         self.username = username
#         self.password = password


@app.route("/", methods = ["GET", "POST"])
@app.route("/login", methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        session.permanent = True
        user = request.form["username"]
        session["username"] = user
        return redirect(url_for("home"))
    else:
        if "user" in session:
            return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    if request.method == "POST":
        session.permanent = True
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]
        session["username"] = username

        # found_user = users.query.filter_by(username = username).first()
        # if found_user:
            # session["username"] = found_user.username
        # else:
        #     user = users(name, username, password)
        #     db.session.add(user)
        #     db.session.commit()
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
        session.pop("username", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    # db.create_all()
    app.run(port=8000, debug=True)
