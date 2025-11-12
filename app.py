from flask import Flask, render_template, url_for, redirect, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

# Import models and database
from models import db, User, Task
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database with app
db.init_app(app)


# ==================== ROUTES ====================

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, redirect to home
    if "username" in session:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
    
        # Validate inputs (in case of malicious user)
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("login.html")
        
        # Query user
        found_user = User.query.filter_by(username=username).first()
        
        # Check user exists AND password is correct
        if found_user and check_password_hash(found_user.password_hash, password):
            session.permanent = True
            session["username"] = found_user.username
            session["user_id"] = found_user.id  # Best Practice: Store user_id, not just username
            flash(f"Welcome back, {found_user.full_name}!", "success")
            return redirect(url_for("home"))
        else:
            # Best Practice: Generic error message (don't reveal if username exists)
            flash("Invalid username or password", "error")
            return render_template("login.html")
    
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # If already logged in, redirect to home
    if "username" in session:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        full_name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # Validate inputs (in case of malicious user)
        if not full_name or not username or not password:
            flash("All fields are required", "error")
            return render_template("register.html")
        
        if len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return render_template("register.html")
        
        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template("register.html")
        
        # Check if username already exists
        found_user = User.query.filter_by(username=username).first()
        
        if found_user:
            flash("Username already taken. Please choose another.", "error")
            return render_template("register.html")
        
        # Best Practice: Try-except for database operations
        try:
            hashed = generate_password_hash(password, method='pbkdf2:sha256')
            user = User(full_name, username, hashed)
            db.session.add(user)
            db.session.commit()
            
            # Log the user in immediately after registration
            session.permanent = True
            session["username"] = user.username
            session["user_id"] = user.id
            
            flash(f"Welcome, {full_name}! Your account has been created.", "success")
            return redirect(url_for("home"))
        
        except Exception as e:
            db.session.rollback()  # Best Practice: Rollback on error
            flash("An error occurred. Please try again.", "error")
            print(f"Registration error: {e}")  # Best Practice: Log errors
            return render_template("register.html")
    
    return render_template("register.html")


@app.route("/home")
def home():
    if "username" not in session:
        flash("Please log in to access this page", "error")
        return redirect(url_for("login"))
    
    username = session["username"]
    # Best Practice: Get fresh user data from database
    user = User.query.filter_by(username=username).first()
    
    if not user:  # Best Practice: Handle case where session has invalid user
        session.clear()
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("login"))
    
    return render_template("home.html", username=user.username, full_name=user.full_name)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("login"))

# development debugging route

@app.route("/debug")
def debug():
    users = User.query.all()
    tasks = Task.query.all()
    
    output = "<h1>Database Debug</h1>"
    
    # Show users
    output += "<h2>Users</h2>"
    output += f"<p>Total users: {len(users)}</p><hr>"
    
    if users:
        for user in users:
            output += f"<p><strong>ID:</strong> {user.id} | "
            output += f"<strong>Username:</strong> {user.username} | "
            output += f"<strong>Name:</strong> {user.full_name} | "
            output += f"<strong>Tasks:</strong> {len(user.tasks)}</p>"
    else:
        output += "<p>No users in database</p>"
    
    # Show tasks
    output += "<hr><h2>Tasks</h2>"
    output += f"<p>Total tasks: {len(tasks)}</p><hr>"
    
    if tasks:
        for task in tasks:
            output += f"<p><strong>ID:</strong> {task.id} | "
            output += f"<strong>Title:</strong> {task.title} | "
            output += f"<strong>User:</strong> {task.user.username} | "
            output += f"<strong>Due:</strong> {task.due_date} | "
            output += f"<strong>Completed:</strong> {task.completed}</p>"
    else:
        output += "<p>No tasks in database</p>"
    
    output += "<hr><a href='/home'>Go to Home</a> | <a href='/login'>Go to Login</a>"
    return output


# ==================== INITIALIZATION ====================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✓ Database tables created successfully")
        
        users_count = User.query.count()
        tasks_count = Task.query.count()
        print(f"✓ Current users in database: {users_count}")
        print(f"✓ Current tasks in database: {tasks_count}")
        
        if users_count > 0:
            print("✓ Sample users:")
            for user in User.query.limit(3).all():
                print(f"  - {user} (Tasks: {len(user.tasks)})")

    app.run(port=8000, debug=True)