import os
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from inte6cz import generate, setupModel, retieve_patient_info, validate, check_score, chosen_model, decision_model, get_info

# Database setup
DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'instance', 'app.sqlite3')}"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Initialize session state
if "model_name" not in st.session_state:
    st.session_state["model_name"] = None
if "authenticated_admin" not in st.session_state:
    st.session_state["authenticated_admin"] = None
if "session_id" not in st.session_state:
    st.session_state["session_id"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "current_info" not in st.session_state:
    st.session_state["current_info"] = ""

# Database models
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

# Function to generate a default session name
def generate_session_name(admin_username):
    return f"Session-{admin_username}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

# Function to save messages to the database
def save_message(role, content):
    db_session = SessionLocal()
    try:
        new_message = Message(
            session_id=st.session_state["session_id"],
            role=role,
            content=content
        )
        db_session.add(new_message)
        db_session.commit()
    finally:
        db_session.close()

# Load custom CSS
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "cb_style", "cb_styles.css")
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Load custom CSS
load_css()

# Check query parameters
query_params = st.query_params

if "admin_id" in query_params and "username" in query_params and "session_id" in query_params:
    admin_id = int(query_params["admin_id"])
    username = query_params["username"]
    session_id = int(query_params["session_id"])

    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=admin_id, username=username).first()
    session_instance = db_session.query(Session).filter_by(session_id=session_id, admin_id=admin_id).first()
    db_session.close()

    if admin and session_instance:
        st.session_state["session_id"] = session_id

        db_session = SessionLocal()
        messages = db_session.query(Message).filter_by(session_id=session_id).order_by(Message.timestamp.asc()).all()

        st.session_state["messages"] = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        db_session.close()
    else:
        st.error("Invalid user or session. Please log in.")
        st.stop()
else:
    st.error("Missing query parameters: admin_id, username, or session_id.")
    st.stop()

# Sidebar for session naming and model selection
st.sidebar.title("Settings")

# Session naming
db_session = SessionLocal()
current_session = db_session.query(Session).filter_by(session_id=st.session_state["session_id"]).first()

if current_session:
    st.sidebar.subheader("Session Naming")
    new_session_name = st.sidebar.text_input("Update session name:", value=current_session.session_name)
    if st.sidebar.button("Save Session Name"):
        current_session.session_name = new_session_name
        db_session.commit()
        st.sidebar.success("Session name updated!")

db_session.close()

# Model selection
st.sidebar.subheader("Model Selection")
model_choice = st.sidebar.radio("Select a model:", options=["GPT", "GEMINI"], index=0)
if st.sidebar.button("Confirm Model Selection"):
    st.session_state["model_name"] = model_choice.lower()
    st.sidebar.success(f"Model selected: {model_choice}")

# Set up the model only after selection
if st.session_state.get("model_name"):
    model = setupModel(st.session_state["model_name"])

# Main content rendering
st.title(f"Welcome, {username}!")

# Display existing chat history
for message in st.session_state["messages"]:
    # For human user, display the username, otherwise show "bot" for the assistant
    role = "row-reverse" if message["role"] != "assistant" else ""
    bubble_class = "human-bubble" if message["role"] != "assistant" else "ai-bubble"
    icon_text = st.session_state.get("username", username) if message["role"] != "assistant" else "Bot"
    
    st.markdown(
        f"""
        <div class="chat-row {role}">
            <div class="chat-icon">{icon_text}</div>
            <div class="chat-bubble {bubble_class}">{message["content"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Handle new input from user
if prompt := st.chat_input("Your message:"):
    st.session_state["messages"].append({"role": username, "content": prompt})
    save_message(username, prompt)

    # Formatting the user message the same way as the previous messages
    st.markdown(
        f"""
        <div class="chat-row row-reverse">
            <div class="chat-icon">{st.session_state.get("username", username)}</div>
            <div class="chat-bubble human-bubble">{prompt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Corn
    st.session_state["current_info"] = retieve_patient_info(prompt, chosen_model, st.session_state["current_info"])
    print("Current Info:", st.session_state["current_info"])  # Debugging: Log current info

    validation = validate(decision_model, st.session_state["current_info"])
    print(validation)  # Debugging: Log validation result

    if check_score(validation):
        response = generate(st.session_state["current_info"], chosen_model)
        print("Recommendation:", response)  # Debugging: Log AI recommendation
    else:
        response = get_info(st.session_state["current_info"], chosen_model)
        print("Response:", response)  # Debugging: Log AI response

    # Formatting the assistant response in the same style
    st.markdown(
        f"""
        <div class="chat-row">
            <div class="chat-icon">Bot</div>
            <div class="chat-bubble ai-bubble">{response}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Save the assistant's response and update session state
    st.session_state["messages"].append({"role": "assistant", "content": response})
    save_message("assistant", response)

