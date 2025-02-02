import os
import subprocess
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload
from datetime import datetime

chatbotapp = Flask(__name__)
chatbotapp.secret_key = "super_secret_key"

# Ensure the instance folder exists
if not os.path.exists(chatbotapp.instance_path):
    os.makedirs(chatbotapp.instance_path)

# Database setup
DATABASE_URL = f"sqlite:///{os.path.join(chatbotapp.instance_path, 'app.sqlite3')}"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class Admin(Base):
    __tablename__ = "admin"
    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    sessions = relationship("Session", back_populates="admin")
    is_admin = Column(Boolean, default=False)

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admin.admin_id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    session_name = Column(String, default="Untitled Session")
    messages = relationship("Message", back_populates="session")
    admin = relationship("Admin", back_populates="sessions")

class Message(Base):
    __tablename__ = "messages"
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="messages")

Base.metadata.create_all(bind=engine)

@chatbotapp.route("/")
def home():
    if session.get("logged_out"):
        flash("You have successfully logged out.", "info")
        session.pop("logged_out", None)
    return render_template("cb_index.html", content="Welcome to the Main Webpage!")

@chatbotapp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db_session = SessionLocal()
        admin = db_session.query(Admin).filter_by(username=username).first()

        if admin and admin.password == password:  # Plain text comparison
            session["admin_id"] = admin.admin_id
            session["username"] = admin.username
            db_session.close()
            # Redirect admins to the admin-specific history page
            if admin.is_admin:
                return redirect(url_for("cb_admin_view_history"))
            return redirect(url_for("success"))
        else:
            db_session.close()
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))
    return render_template("cb_login.html")

@chatbotapp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        db_session = SessionLocal()
        if db_session.query(Admin).filter_by(username=username).first():
            db_session.close()
            error = "Username already exists."
            flash("Username already exists.")
            return render_template("cb_register.html", error=error)
        # Create a new admin with is_admin set to False
        new_admin = Admin(
            username=username,
            email=email,
            password=password,
            is_admin=False  # Explicitly set is_admin to False
        )
        
        db_session.add(new_admin)
        db_session.commit()
        db_session.close()
        
        flash("Registration successful! You can now log in.", "success")
        
        return redirect(url_for("home"))
    return render_template("cb_register.html")


@chatbotapp.route("/create_admin", methods=["GET", "POST"])
def create_admin():
    if "admin_id" not in session:
        return redirect(url_for("home"))
    
    # Retrieve the logged-in admin
    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=session["admin_id"]).first()
    if not admin or not admin.is_admin:
        db_session.close()
        flash("Unauthorized access. Only admins can create new user/admin.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        is_admin = request.form.get("is_admin") == "on"  # Handle checkbox value

        # Check if the username already exists
        if db_session.query(Admin).filter_by(username=username).first():
            db_session.close()
            error = "Username already exists."
            return render_template("cb_create_admin.html", error=error)

        # Create the new admin/user
        new_admin = Admin(
            username=username,
            email=email,
            password=password,
            is_admin=is_admin  # Set based on checkbox value
        )
        db_session.add(new_admin)
        db_session.commit()
        db_session.close()

        success = f"User '{username}' created successfully. Admin status: {'Yes' if is_admin else 'No'}."
        return render_template("cb_create_admin.html", success=success)

    db_session.close()
    return render_template("cb_create_admin.html", username=admin.username)



@chatbotapp.route("/cb_admin_view_history", methods=["GET", "POST"])
def cb_admin_view_history():
    # Redirect to login if the user is not authenticated
    if "admin_id" not in session:
        flash("You must be logged in as an admin to view chat history.", "warning")
        return redirect(url_for("login"))

    db_session = SessionLocal()

    # Retrieve the logged-in admin
    admin = db_session.query(Admin).filter_by(admin_id=session["admin_id"]).first()
    if not admin or not admin.is_admin:
        db_session.close()
        flash("Unauthorized access. Only admins can view chat history.", "danger")
        return redirect(url_for("home"))

    # Search and Pagination
    search_query = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    query = db_session.query(Session).join(Admin).options(joinedload(Session.admin))

    # Apply search filter
    if search_query:
        query = query.filter(Admin.username.ilike(f"%{search_query}%"))  # Search by username

    # Sort alphabetically by admin username
    query = query.order_by(Admin.username.asc())

    # Total number of sessions for pagination
    total_sessions = query.count()

    # Retrieve sessions for the current page
    history = query.offset(offset).limit(per_page).all()

    db_session.close()

    # Render the template with filtered results and pagination
    return render_template(
        "cb_admin_view_history.html",
        username=admin.username,
        is_admin=admin.is_admin,
        history=history,
        search_query=search_query,
        page=page,
        total_pages=(total_sessions + per_page - 1) // per_page,
        current_admin_id=admin.admin_id,  # Pass the logged-in admin's ID to template
    )




@chatbotapp.route("/view_history")
def view_history():
    if "admin_id" not in session:
        flash("You must be logged in as a user or admin to view chat history.", "warning")
        return redirect(url_for("login"))

    admin_id = session["admin_id"]
    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=admin_id).first()

    if not admin:
        db_session.close()
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for("login"))

    if admin.is_admin:
        db_session.close()
        return redirect(url_for("cb_admin_view_history"))

    # Query only the user's sessions
    history = db_session.query(Session).filter_by(admin_id=admin_id).all()
    
    # Explicitly pass session IDs for deletion handling
    session_data = [
        {
            "session_id": session.session_id,
            "session_name": session.session_name,
            "start_time": session.start_time.strftime('%Y-%m-%d'),
        }
        for session in history
    ]

    db_session.close()

    return render_template(
        "cb_view_history.html",
        username=admin.username,
        history=session_data,  # Updated to a structured list
    )


@chatbotapp.route("/delete_session/<int:session_id>", methods=["POST"])
def delete_session(session_id):
    if "admin_id" not in session:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("view_history"))

    admin_id = session["admin_id"]
    db_session = SessionLocal()
    session_to_delete = db_session.query(Session).filter_by(session_id=session_id, admin_id=admin_id).first()

    if not session_to_delete:
        db_session.close()
        flash("Session not found or unauthorized.", "danger")
        return redirect(url_for("view_history"))

    # Delete related messages first (to maintain referential integrity)
    db_session.query(Message).filter_by(session_id=session_id).delete()

    # Delete the session itself
    db_session.delete(session_to_delete)
    db_session.commit()
    db_session.close()

    flash("Session deleted successfully.", "success")
    return redirect(url_for("view_history"))




@chatbotapp.route("/chat")
def chat():
    if "admin_id" not in session or "username" not in session:
        flash("You must be logged in to access chat.", "warning")
        return redirect(url_for("login"))

    admin_id = session.get("admin_id")
    username = session.get("username")
    session_id = request.args.get("session_id")
    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=admin_id).first()

    if not admin:
        db_session.close()
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for("login"))

    if session_id:
        existing_session = db_session.query(Session).filter_by(session_id=session_id).first()
        if not existing_session:
            db_session.close()
            flash("Session not found.", "danger")
            return redirect(url_for("success"))

        # Admins can view all sessions but cannot modify those they don’t own
        is_read_only = admin.is_admin and existing_session.admin_id != admin_id
        streamlit_url = f"http://localhost:8501/?admin_id={admin_id}&username={username}&session_id={session_id}&read_only={is_read_only}"
    else:
        # Allow admins to create new sessions
        new_session = Session(admin_id=admin_id)
        db_session.add(new_session)
        db_session.commit()
        session_id = new_session.session_id
        streamlit_url = f"http://localhost:8501/?admin_id={admin_id}&username={username}&session_id={session_id}&read_only=False"

    db_session.close()

    # Start Streamlit on port 8501
    streamlit_path = os.path.join(os.getcwd(), "frontend.py")
    subprocess.Popen(
        [
            "python", "-m", "streamlit", "run", streamlit_path,
            "--server.port", "8501", "--server.headless", "true"
        ]
    )

    webbrowser.open_new(streamlit_url)
    return redirect(url_for("success"))




@chatbotapp.route("/delete_user", methods=["GET", "POST"])
def cb_delete_user():
    # Redirect to login if the user is not authenticated
    if "admin_id" not in session:
        flash("You must be logged in as an admin to view users.", "warning")
        return redirect(url_for("login"))

    db_session = SessionLocal()

    # Retrieve the logged-in admin
    admin = db_session.query(Admin).filter_by(admin_id=session["admin_id"]).first()
    if not admin or not admin.is_admin:
        db_session.close()
        flash("Unauthorized access. Only admins can view and delete users.", "danger")
        return redirect(url_for("home"))

    # Search and Pagination
    search_query = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    # Query users excluding admins
    query = db_session.query(Admin).filter(Admin.is_admin == False)

    # Apply search filter (by username only)
    if search_query:
        query = query.filter(Admin.username.ilike(f"%{search_query}%"))

    # Sort alphabetically by username
    query = query.order_by(Admin.username.asc())

    # Total number of users for pagination
    total_users = query.count()

    # Retrieve users for the current page
    users = query.offset(offset).limit(per_page).all()

    # Get session count for each user
    users_with_sessions = []
    for user in users:
        session_count = db_session.query(Session).filter_by(admin_id=user.admin_id).count()
        users_with_sessions.append({"user": user, "session_count": session_count})

    db_session.close()

    # Render the template with filtered results and pagination
    return render_template(
        "cb_delete_user.html",
        username=admin.username,
        is_admin=admin.is_admin,
        users_with_sessions=users_with_sessions,
        search_query=search_query,
        page=page,
        total_pages=(total_users + per_page - 1) // per_page,
    )



@chatbotapp.route("/delete_user/<int:user_id>", methods=["GET", "POST"])
def delete_user(user_id):
    # Redirect to login if the user is not authenticated
    if "admin_id" not in session:
        flash("You must be logged in as an admin to delete users.", "warning")
        return redirect(url_for("login"))

    db_session = SessionLocal()

    try:
        # Retrieve the logged-in admin
        admin = db_session.query(Admin).filter_by(admin_id=session["admin_id"]).first()
        if not admin or not admin.is_admin:
            flash("Unauthorized access. Only admins can delete users.", "danger")
            return redirect(url_for("home"))

        # Retrieve the user to be deleted
        user_to_delete = db_session.query(Admin).filter_by(admin_id=user_id).first()
        if not user_to_delete:
            flash("User not found.", "danger")
            return redirect(url_for("cb_delete_user"))

        # Handle the deletion of user and their related sessions/messages
        if request.method == "POST":
            # Delete associated messages in bulk
            db_session.query(Message).filter(Message.session_id.in_(
                [session.session_id for session in user_to_delete.sessions]
            )).delete(synchronize_session='fetch')

            # Delete the user's sessions
            db_session.query(Session).filter_by(admin_id=user_id).delete(synchronize_session='fetch')

            # Delete the user from the Admin table
            db_session.delete(user_to_delete)
            db_session.commit()

            flash(f"User '{user_to_delete.username}' and all their data have been deleted.", "success")
            return redirect(url_for("cb_delete_user"))

        # Render the delete confirmation page
        return render_template(
            "cb_delete_user_confirm.html",
            username=admin.username,
            user_to_delete=user_to_delete,
        )
    finally:
        db_session.close()


@chatbotapp.route("/success")
def success():
    return redirect(url_for("view_history"))

@chatbotapp.route("/logout")
def logout():
    session.clear()
    session["logged_out"] = True
    return redirect(url_for("home"))



if __name__ == "__main__":
    chatbotapp.run(debug=True, port=5000)
