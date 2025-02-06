import os
import sys
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

class User(Base):
    __tablename__ = "user"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    sessions = relationship("Session", back_populates="user")
    is_admin = Column(Boolean, default=False)

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    session_name = Column(String, default="Untitled Session")
    messages = relationship("Message", back_populates="session")
    user = relationship("User", back_populates="sessions")

class Message(Base):
    __tablename__ = "messages"
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    feedback = Column(Integer, nullable=True)
    session = relationship("Session", back_populates="messages")

Base.metadata.create_all(bind=engine)

# HOME
@chatbotapp.route("/")
def home():
    if session.get("logged_out"):
        flash("You have successfully logged out.", "info")
        session.pop("logged_out", None)
    return render_template("cb_index.html", content="Welcome to the Main Webpage!")


# LOGIN
@chatbotapp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db_session = SessionLocal()
        user = db_session.query(User).filter_by(username=username).first()

        if user and user.password == password: 
            session["user_id"] = user.user_id
            session["username"] = user.username
            db_session.close()
            if user.is_admin:
                return redirect(url_for("cb_user_view_history"))
            return redirect(url_for("success"))
        else:
            db_session.close()
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))
    return render_template("cb_login.html")


#REGISTER
@chatbotapp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        db_session = SessionLocal()
        if db_session.query(User).filter_by(username=username).first():
            db_session.close()
            error = "Username already exists."
            flash("Username already exists.")
            return render_template("cb_register.html", error=error)
        new_user = User(
            username=username,
            email=email,
            password=password,
            is_admin=False 
        )
        
        db_session.add(new_user)
        db_session.commit()
        db_session.close()
        
        flash("Registration successful! You can now log in.", "success")
        
        return redirect(url_for("home"))
    return render_template("cb_register.html")


# CREATE USER
@chatbotapp.route("/create_user", methods=["GET", "POST"])
def create_user():
    if "user_id" not in session:
        return redirect(url_for("home"))
    
    db_session = SessionLocal()
    user = db_session.query(User).filter_by(user_id=session["user_id"]).first()
    if not user or not user.is_admin:
        db_session.close()
        flash("Unauthorized access. Only users can create new user/user.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if db_session.query(User).filter_by(username=username).first():
            db_session.close()
            error = "Username already exists."
            return render_template("cb_create_user.html", error=error)

        new_user = User(
            username=username,
            email=email,
            password=password,
            is_admin= False #
        )
        db_session.add(new_user)
        db_session.commit()
        db_session.close()

        success = f"User '{username}' created successfully."
        return render_template("cb_create_user.html", success=success)

    db_session.close()
    return render_template("cb_create_user.html", username=user.username)


# ADMIN DASHBOARD
@chatbotapp.route("/cb_admin_view_history", methods=["GET", "POST"])
def cb_user_view_history():
    if "user_id" not in session:
        flash("You must be logged in as an user to view chat history.", "warning")
        return redirect(url_for("login"))

    db_session = SessionLocal()

    user = db_session.query(User).filter_by(user_id=session["user_id"]).first()
    if not user or not user.is_admin:
        db_session.close()
        flash("Unauthorized access. Only users can view chat history.", "danger")
        return redirect(url_for("home"))

    search_query = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    query = db_session.query(Session).join(User).options(joinedload(Session.user))

    if search_query:
        query = query.filter(User.username.ilike(f"%{search_query}%")) 
    query = query.order_by(User.username.asc())
    total_sessions = query.count()
    history = query.offset(offset).limit(per_page).all()
    db_session.close()
    
    return render_template(
        "cb_admin_view_history.html",
        username=user.username,
        is_admin=user.is_admin,
        history=history,
        search_query=search_query,
        page=page,
        total_pages=(total_sessions + per_page - 1) // per_page,
        current_user_id=user.user_id,  
    )

# USER DASHBOARD
@chatbotapp.route("/view_history")
def view_history():
    if "user_id" not in session:
        flash("You must be logged in as a user or user to view chat history.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    db_session = SessionLocal()
    user = db_session.query(User).filter_by(user_id=user_id).first()

    if not user:
        db_session.close()
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for("login"))

    if user.is_admin:
        db_session.close()
        return redirect(url_for("cb_user_view_history"))

    # Query only the user's sessions
    history = db_session.query(Session).filter_by(user_id=user_id).all()
    
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
        username=user.username,
        history=session_data,  # Updated to a structured list
    )

# CHATBOT
@chatbotapp.route("/chat")
def chat():
    if "user_id" not in session or "username" not in session:
        flash("You must be logged in to access chat.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    username = session.get("username")
    session_id = request.args.get("session_id")
    db_session = SessionLocal()
    user = db_session.query(User).filter_by(user_id=user_id).first()

    if not user:
        db_session.close()
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for("login"))

    if session_id:
        existing_session = db_session.query(Session).filter_by(session_id=session_id).first()
        if not existing_session:
            db_session.close()
            flash("Session not found.", "danger")
            return redirect(url_for("success"))
        is_read_only = user.is_admin and existing_session.user_id != user_id
        streamlit_url = f"http://localhost:8501/?user_id={user_id}&username={username}&session_id={session_id}&read_only={is_read_only}"
    else:
        new_session = Session(user_id=user_id)
        db_session.add(new_session)
        db_session.commit()
        session_id = new_session.session_id
        streamlit_url = f"http://localhost:8501/?user_id={user_id}&username={username}&session_id={session_id}&read_only=False"

    db_session.close()

    # Start Streamlit on port 8501
    streamlit_path = os.path.join(os.getcwd(), "frontend.py")
    subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", streamlit_path,
            "--server.port", "8501", "--server.headless", "true"
        ]
    )

    webbrowser.open_new(streamlit_url)
    return redirect(url_for("success"))

# DELETE USER SESSION
@chatbotapp.route("/delete_session/<int:session_id>", methods=["POST"])
def delete_session(session_id):
    if "user_id" not in session:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("view_history"))
    user_id = session["user_id"]
    db_session = SessionLocal()
    session_to_delete = db_session.query(Session).filter_by(session_id=session_id, user_id=user_id).first()
    if not session_to_delete:
        db_session.close()
        flash("Session not found or unauthorized.", "danger")
        return redirect(url_for("view_history"))
    db_session.query(Message).filter_by(session_id=session_id).delete()
    db_session.delete(session_to_delete)
    db_session.commit()
    db_session.close()
    flash("Session deleted successfully.", "success")
    return redirect(url_for("view_history"))

# DELETE USER [FOR ADMIN USE ONLY]
@chatbotapp.route("/delete_user", methods=["GET", "POST"])
def cb_delete_user():
    if "user_id" not in session:
        flash("You must be logged in as an user to view users.", "warning")
        return redirect(url_for("login"))
    db_session = SessionLocal()
    user = db_session.query(User).filter_by(user_id=session["user_id"]).first()
    if not user or not user.is_admin:
        db_session.close()
        flash("Unauthorized access. Only users can view and delete users.", "danger")
        return redirect(url_for("home"))
    search_query = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page
    query = db_session.query(User).filter(User.is_admin == False)
    if search_query:
        query = query.filter(User.username.ilike(f"%{search_query}%"))
    query = query.order_by(User.username.asc())
    total_users = query.count()
    users = query.offset(offset).limit(per_page).all()
    users_with_sessions = []
    for user in users:
        session_count = db_session.query(Session).filter_by(user_id=user.user_id).count()
        users_with_sessions.append({"user": user, "session_count": session_count})
    db_session.close()
    return render_template(
        "cb_delete_user.html",
        username=user.username,
        is_admin=user.is_admin,
        users_with_sessions=users_with_sessions,
        search_query=search_query,
        page=page,
        total_pages=(total_users + per_page - 1) // per_page,
    )


# DELETE USER [ADMIN USE ONLY]
@chatbotapp.route("/delete_user/<int:user_id>", methods=["GET", "POST"])
def delete_user(user_id):
    if "user_id" not in session:
        flash("You must be logged in as an user to delete users.", "warning")
        return redirect(url_for("login"))
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(user_id=session["user_id"]).first()
        if not user or not user.is_admin:
            flash("Unauthorized access. Only users can delete users.", "danger")
            return redirect(url_for("home"))
        user_to_delete = db_session.query(User).filter_by(user_id=user_id).first()
        if not user_to_delete:
            flash("User not found.", "danger")
            return redirect(url_for("cb_delete_user"))
        if request.method == "POST":
            db_session.query(Message).filter(Message.session_id.in_(
                [session.session_id for session in user_to_delete.sessions]
            )).delete(synchronize_session='fetch')
            db_session.query(Session).filter_by(user_id=user_id).delete(synchronize_session='fetch')
            db_session.delete(user_to_delete)
            db_session.commit()
            flash(f"User '{user_to_delete.username}' and all their data have been deleted.", "success")
            return redirect(url_for("cb_delete_user"))
        return render_template(
            "cb_delete_user_confirm.html",
            username=user.username,
            user_to_delete=user_to_delete,
        )
    finally:
        db_session.close()


# FOR LOGIN
@chatbotapp.route("/success")
def success():
    return redirect(url_for("view_history"))

@chatbotapp.route("/logout")
def logout():
    session.clear()
    session["logged_out"] = True
    return redirect(url_for("home"))


# MAIN PORT
if __name__ == "__main__":
    chatbotapp.run(debug=False, port=5000)
