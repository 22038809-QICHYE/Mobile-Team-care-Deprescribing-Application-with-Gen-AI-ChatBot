import os
import subprocess
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


chatbotapp = Flask(__name__)
chatbotapp.secret_key = "super_secret_key"

# Database setup
DATABASE_URL =  "sqlite:///app.sqlite3"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    sessions = relationship("Session", back_populates="admin")
    is_admin = Column(Boolean, default=False)


class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
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
# Define global variables for admin information
username = None  # Global variable for username
admin_id = None    # Global variable for admin_id


@chatbotapp.route("/")
def home():
    return render_template("cb_index.html")

@chatbotapp.route("/login", methods=["GET", "POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    db_session = SessionLocal()

    admin = db_session.query(Admin).filter_by(username=username).first()
    if admin and admin.password == password:  # Direct comparison of plain passwords
        session["admin_id"] = admin.admin_id
        session["username"] = admin.username
        db_session.close()
        return redirect(url_for("success"))
    else:
        db_session.close()
        error = "Invalid username or password."
        return render_template("cb_login.html", error=error)


@chatbotapp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        db_session = SessionLocal()

        if db_session.query(Admin).filter_by(username=username).first():
            db_session.close()
            error = "Adminname already exists."
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
        return redirect(url_for("home"))

    return render_template("cb_register.html")


@chatbotapp.route("/success")
def success():
    if "admin_id" not in session:
        return redirect(url_for("home"))
    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=session["admin_id"]).first()
    db_session.close()

    if admin.is_admin:
        return render_template("cb_index_admin.html", username=admin.username)
    else:
        return render_template("cb_index_user.html", username=admin.username)

@chatbotapp.route("/create_admin", methods=["GET", "POST"])
def create_admin():
    if "admin_id" not in session:
        return redirect(url_for("home"))
    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=session["admin_id"]).first()
    if not admin or not admin.is_admin:
        db_session.close()
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if db_session.query(Admin).filter_by(username=username).first():
            db_session.close()
            error = "Username already exists."
            return render_template("cb_create_admin.html", error=error)

        new_admin = Admin(
            username=username,
            email=email,
            password=password,
            is_admin=True
        )
        db_session.add(new_admin)
        db_session.commit()
        db_session.close()
        return redirect(url_for("success"))

    return render_template("cb_create_admin.html")


@chatbotapp.route("/chat")
def chat():
    if "admin_id" not in session:
        return redirect(url_for("home"))

    global username, admin_id
    admin_id = session["admin_id"]
    username = session["username"]

    # Create a new session for the admin
    db_session = SessionLocal()
    new_session = Session(admin_id=admin_id)
    db_session.add(new_session)
    db_session.commit()
    session_id = new_session.session_id
    db_session.close()

    # Pass session_id to the frontend
    streamlit_path = os.path.join(os.getcwd(), "frontend.py")
    streamlit_url = f"http://localhost:8501/?admin_id={admin_id}&username={username}&session_id={session_id}"

    # Start Streamlit on port 8501
    subprocess.Popen(
        [
            "python",
            "-m", "streamlit", "run", streamlit_path,
            "--server.port", "8501",
            "--server.headless", "true"
        ]
    )

    # Automatically open the URL in the default web browser
    webbrowser.open_new(streamlit_url)

    return f"Streamlit Chatbot is starting... Session ID: {session_id}"



@chatbotapp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    chatbotapp.run(debug=True)
