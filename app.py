from flask import Flask, render_template, url_for, redirect, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime

# Import models and database
from models import db, User, Task
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database with app
db.init_app(app)


# ==================== AUTHENTICATION ROUTES ====================

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if "username" in session:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("login.html")
        
        found_user = User.query.filter_by(username=username).first()
        
        if found_user and check_password_hash(found_user.password_hash, password):
            session.permanent = True
            session["username"] = found_user.username
            session["user_id"] = found_user.id
            flash(f"Welcome back, {found_user.full_name}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password", "error")
            return render_template("login.html")
    
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration"""
    if "username" in session:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        full_name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not full_name or not username or not password:
            flash("All fields are required", "error")
            return render_template("register.html")
        
        if len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return render_template("register.html")
        
        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template("register.html")
        
        found_user = User.query.filter_by(username=username).first()
        
        if found_user:
            flash("Username already taken. Please choose another.", "error")
            return render_template("register.html")
        
        try:
            hashed = generate_password_hash(password, method='pbkdf2:sha256')
            user = User(full_name, username, hashed)
            db.session.add(user)
            db.session.commit()
            
            session.permanent = True
            session["username"] = user.username
            session["user_id"] = user.id
            
            flash(f"Welcome, {full_name}! Your account has been created.", "success")
            return redirect(url_for("home"))
        
        except Exception as e:
            db.session.rollback()
            flash("An error occurred. Please try again.", "error")
            print(f"Registration error: {e}")
            return render_template("register.html")
    
    return render_template("register.html")


@app.route("/logout", methods=["POST"])
def logout():
    """Handle user logout"""
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("login"))


# ==================== HOME PAGE ====================

@app.route("/home")
def home():
    """Home page with task display"""
    if "username" not in session:
        flash("Please log in to access this page", "error")
        return redirect(url_for("login"))
    
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("login"))
    
    # Get active tab
    active_tab = request.args.get('tab', 'today')
    valid_tabs = ['today', 'past', 'future']
    if active_tab not in valid_tabs:
        active_tab = 'today'
    
    # Get today's date
    today = date.today()
    
    # Query tasks based on tab
    if active_tab == 'today':
        tasks = Task.query.filter_by(
            user_id=user_id,
            due_date=today
        ).order_by(Task.priority).all()
    
    elif active_tab == 'past':
        tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date < today,
            Task.completed == True
        ).order_by(Task.due_date.desc()).all()
    
    else:  # future
        tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date > today
        ).order_by(Task.due_date).all()
    
    # Split into ongoing and complete
    ongoing_tasks = [t for t in tasks if not t.completed]
    complete_tasks = [t for t in tasks if t.completed]
    
    return render_template('home.html',
                         username=user.username,
                         full_name=user.full_name,
                         active_tab=active_tab,
                         ongoing_tasks=ongoing_tasks,
                         complete_tasks=complete_tasks)


# ==================== TASK CRUD OPERATIONS ====================

@app.route("/new-task", methods=["GET", "POST"])
def new_task():
    """Create a new task"""
    if "user_id" not in session:
        flash("Please log in to create tasks", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date_str = request.form.get("due_date", "")
        
        # Validation
        if not title:
            flash("Task title is required", "error")
            return render_template("new_task.html")
        
        if not due_date_str:
            flash("Due date is required", "error")
            return render_template("new_task.html")
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "error")
            return render_template("new_task.html")
        
        # Get highest priority for this user and date
        max_priority = db.session.query(db.func.max(Task.priority)).filter_by(
            user_id=session['user_id'],
            due_date=due_date
        ).scalar() or 0
        
        # Create task
        try:
            task = Task(
                user_id=session['user_id'],
                title=title,
                description=description if description else None,
                due_date=due_date,
                completed=False,
                priority=max_priority + 1
            )
            db.session.add(task)
            db.session.commit()
            
            flash(f"Task '{title}' created successfully!", "success")
            
            # Redirect to appropriate tab
            today = date.today()
            if due_date == today:
                return redirect(url_for("home", tab="today"))
            elif due_date < today:
                return redirect(url_for("home", tab="past"))
            else:
                return redirect(url_for("home", tab="future"))
        
        except Exception as e:
            db.session.rollback()
            flash("Error creating task. Please try again.", "error")
            print(f"Task creation error: {e}")
            return render_template("new_task.html")
    
    return render_template("new_task.html")


@app.route("/edit-task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    """Edit an existing task"""
    if "user_id" not in session:
        flash("Please log in to edit tasks", "error")
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    # Verify task belongs to current user
    if task.user_id != session['user_id']:
        flash("You don't have permission to edit this task", "error")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date_str = request.form.get("due_date", "")
        
        if not title:
            flash("Task title is required", "error")
            return render_template("edit_task.html", task=task)
        
        if not due_date_str:
            flash("Due date is required", "error")
            return render_template("edit_task.html", task=task)
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "error")
            return render_template("edit_task.html", task=task)
        
        try:
            task.title = title
            task.description = description if description else None
            task.due_date = due_date
            db.session.commit()
            
            flash(f"Task '{title}' updated successfully!", "success")
            
            # Redirect to appropriate tab
            today = date.today()
            if due_date == today:
                return redirect(url_for("home", tab="today"))
            elif due_date < today:
                return redirect(url_for("home", tab="past"))
            else:
                return redirect(url_for("home", tab="future"))
        
        except Exception as e:
            db.session.rollback()
            flash("Error updating task. Please try again.", "error")
            print(f"Task update error: {e}")
            return render_template("edit_task.html", task=task)
    
    return render_template("edit_task.html", task=task)


@app.route("/delete-task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    """Delete a task"""
    if "user_id" not in session:
        flash("Please log in to delete tasks", "error")
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash("You don't have permission to delete this task", "error")
        return redirect(url_for("home"))
    
    # Get tab before deleting
    today = date.today()
    if task.due_date == today:
        tab = "today"
    elif task.due_date < today:
        tab = "past"
    else:
        tab = "future"
    
    try:
        title = task.title
        db.session.delete(task)
        db.session.commit()
        flash(f"Task '{title}' deleted", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting task", "error")
        print(f"Delete error: {e}")
    
    return redirect(url_for("home", tab=tab))


@app.route("/toggle-complete/<int:task_id>", methods=["POST"])
def toggle_complete(task_id):
    """Toggle task completion status"""
    if "user_id" not in session:
        flash("Please log in", "error")
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash("You don't have permission to modify this task", "error")
        return redirect(url_for("home"))
    
    # Get current tab
    tab = request.form.get("tab", "today")
    
    try:
        task.completed = not task.completed
        task.completed_at = datetime.now() if task.completed else None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Error updating task", "error")
        print(f"Toggle error: {e}")
    
    return redirect(url_for("home", tab=tab))


@app.route("/reorder-task/<int:task_id>", methods=["POST"])
def reorder_task(task_id):
    """Reorder a task (move up or down)"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        return redirect(url_for("home"))
    
    direction = request.args.get("direction", "up")
    tab = request.form.get("tab", "today")
    
    # Get all tasks for same user and date, ordered by priority
    tasks = Task.query.filter_by(
        user_id=session['user_id'],
        due_date=task.due_date,
        completed=task.completed
    ).order_by(Task.priority).all()
    
    try:
        # Find current position
        current_index = tasks.index(task)
        
        if direction == "up" and current_index > 0:
            # Swap with previous task
            other_task = tasks[current_index - 1]
            task.priority, other_task.priority = other_task.priority, task.priority
            db.session.commit()
        
        elif direction == "down" and current_index < len(tasks) - 1:
            # Swap with next task
            other_task = tasks[current_index + 1]
            task.priority, other_task.priority = other_task.priority, task.priority
            db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        print(f"Reorder error: {e}")
    
    return redirect(url_for("home", tab=tab))


# ==================== DEBUG ROUTE ====================

@app.route("/debug")
def debug():
    """Debug route to view database contents"""
    users = User.query.all()
    tasks = Task.query.all()
    
    output = "<h1>Database Debug</h1>"
    
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
    
    output += "<hr><h2>Tasks</h2>"
    output += f"<p>Total tasks: {len(tasks)}</p><hr>"
    
    if tasks:
        for task in tasks:
            output += f"<p><strong>ID:</strong> {task.id} | "
            output += f"<strong>Title:</strong> {task.title} | "
            output += f"<strong>User:</strong> {task.user.username} | "
            output += f"<strong>Due:</strong> {task.due_date} | "
            output += f"<strong>Completed:</strong> {task.completed} | "
            output += f"<strong>Priority:</strong> {task.priority}</p>"
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
    
    print("\n" + "="*50)
    print("Starting Shinxity server on http://localhost:8000")
    print("="*50 + "\n")
    
    app.run(port=8000, debug=True)
# Import models and database
from models import db, User, Task
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

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
    
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("login"))
    
    # Get active tab
    active_tab = request.args.get('tab', 'today')
    valid_tabs = ['today', 'past', 'future']
    if active_tab not in valid_tabs:
        active_tab = 'today'
    
    # Get today's date
    today = date.today()
    
    # Query tasks based on tab
    if active_tab == 'today':
        tasks = Task.query.filter_by(
            user_id=user_id,
            due_date=today
        ).order_by(Task.priority).all()
    
    elif active_tab == 'past':
        tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date < today,
            Task.completed == True
        ).order_by(Task.due_date.desc()).all()
    
    else:  # future
        tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date > today
        ).order_by(Task.due_date).all()
    
    # Split into ongoing and complete
    ongoing_tasks = [t for t in tasks if not t.completed]
    complete_tasks = [t for t in tasks if t.completed]
    
    return render_template('home.html',
                            username=user.username,
                            full_name=user.full_name,
                            active_tab=active_tab,
                            ongoing_tasks=ongoing_tasks,
                            complete_tasks=complete_tasks)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("login"))


@app.route("/new-task", methods=["GET", "POST"])
def new_task():
    if "user_id" not in session:
        flash("Please log in to create tasks", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date_str = request.form.get("due_date", "")
        
        # Validation
        if not title:
            flash("Task title is required", "error")
            return render_template("new_task.html")
        
        if not due_date_str:
            flash("Due date is required", "error")
            return render_template("new_task.html")
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "error")
            return render_template("new_task.html")
        
        # Get highest priority for this user and date
        max_priority = db.session.query(db.func.max(Task.priority)).filter_by(
            user_id=session['user_id'],
            due_date=due_date
        ).scalar() or 0
        
        # Create task
        try:
            task = Task(
                user_id=session['user_id'],
                title=title,
                description=description if description else None,
                due_date=due_date,
                completed=False,
                priority=max_priority + 1
            )
            db.session.add(task)
            db.session.commit()
            
            flash(f"Task '{title}' created successfully!", "success")
            
            # Redirect to appropriate tab
            today = date.today()
            if due_date == today:
                return redirect(url_for("home", tab="today"))
            elif due_date < today:
                return redirect(url_for("home", tab="past"))
            else:
                return redirect(url_for("home", tab="future"))
        
        except Exception as e:
            db.session.rollback()
            flash("Error creating task. Please try again.", "error")
            print(f"Task creation error: {e}")
            return render_template("new_task.html")
    
    return render_template("new_task.html")


@app.route("/edit-task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if "user_id" not in session:
        flash("Please log in to edit tasks", "error")
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    # Verify task belongs to current user
    if task.user_id != session['user_id']:
        flash("You don't have permission to edit this task", "error")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date_str = request.form.get("due_date", "")
        
        if not title:
            flash("Task title is required", "error")
            return render_template("edit_task.html", task=task)
        
        if not due_date_str:
            flash("Due date is required", "error")
            return render_template("edit_task.html", task=task)
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "error")
            return render_template("edit_task.html", task=task)
        
        try:
            task.title = title
            task.description = description if description else None
            task.due_date = due_date
            db.session.commit()
            
            flash(f"Task '{title}' updated successfully!", "success")
            
            # Redirect to appropriate tab
            today = date.today()
            if due_date == today:
                return redirect(url_for("home", tab="today"))
            elif due_date < today:
                return redirect(url_for("home", tab="past"))
            else:
                return redirect(url_for("home", tab="future"))
        
        except Exception as e:
            db.session.rollback()
            flash("Error updating task. Please try again.", "error")
            print(f"Task update error: {e}")
            return render_template("edit_task.html", task=task)
    
    return render_template("edit_task.html", task=task)


@app.route("/delete-task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    if "user_id" not in session:
        flash("Please log in to delete tasks", "error")
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash("You don't have permission to delete this task", "error")
        return redirect(url_for("home"))
    
    # Get tab before deleting
    today = date.today()
    if task.due_date == today:
        tab = "today"
    elif task.due_date < today:
        tab = "past"
    else:
        tab = "future"
    
    try:
        title = task.title
        db.session.delete(task)
        db.session.commit()
        flash(f"Task '{title}' deleted", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting task", "error")
        print(f"Delete error: {e}")
    
    return redirect(url_for("home", tab=tab))


@app.route("/toggle-complete/<int:task_id>", methods=["POST"])
def toggle_complete(task_id):
    if "user_id" not in session:
        flash("Please log in", "error")
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        flash("You don't have permission to modify this task", "error")
        return redirect(url_for("home"))
    
    # Get current tab
    tab = request.form.get("tab", "today")
    
    try:
        task.completed = not task.completed
        task.completed_at = datetime.now() if task.completed else None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Error updating task", "error")
        print(f"Toggle error: {e}")
    
    return redirect(url_for("home", tab=tab))


@app.route("/reorder-task/<int:task_id>", methods=["POST"])
def reorder_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != session['user_id']:
        return redirect(url_for("home"))
    
    direction = request.args.get("direction", "up")
    tab = request.form.get("tab", "today")
    
    # Get all tasks for same user and date, ordered by priority
    tasks = Task.query.filter_by(
        user_id=session['user_id'],
        due_date=task.due_date,
        completed=task.completed
    ).order_by(Task.priority).all()
    
    try:
        # Find current position
        current_index = tasks.index(task)
        
        if direction == "up" and current_index > 0:
            # Swap with previous task
            other_task = tasks[current_index - 1]
            task.priority, other_task.priority = other_task.priority, task.priority
            db.session.commit()
        
        elif direction == "down" and current_index < len(tasks) - 1:
            # Swap with next task
            other_task = tasks[current_index + 1]
            task.priority, other_task.priority = other_task.priority, task.priority
            db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        print(f"Reorder error: {e}")
    
    return redirect(url_for("home", tab=tab))

# development debugging route

@app.route("/debug")
def debug():
    """Debug route to view database contents"""
    users = User.query.all()
    tasks = Task.query.all()
    
    output = "<h1>Database Debug</h1>"
    
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
    
    output += "<hr><h2>Tasks</h2>"
    output += f"<p>Total tasks: {len(tasks)}</p><hr>"
    
    if tasks:
        for task in tasks:
            output += f"<p><strong>ID:</strong> {task.id} | "
            output += f"<strong>Title:</strong> {task.title} | "
            output += f"<strong>User:</strong> {task.user.username} | "
            output += f"<strong>Due:</strong> {task.due_date} | "
            output += f"<strong>Completed:</strong> {task.completed} | "
            output += f"<strong>Priority:</strong> {task.priority}</p>"
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
    
    print("\n" + "="*50)
    print("Starting Shinxity server on http://localhost:8000")
    print("="*50 + "\n")
    
    app.run(port=8000, debug=True)