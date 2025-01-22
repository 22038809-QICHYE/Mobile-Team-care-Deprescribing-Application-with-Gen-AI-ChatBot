import os
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import pandas as pd
from inte6cz import generate, setupModel, retieve_patient_info, validate, check_score, chosen_model, decision_model, get_info #corn

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
    db_session = SessionLocal()  # Start a session with the database
    try:
        # Create a new message record
        new_message = Message(
            session_id=st.session_state["session_id"],  # Use the current session ID
            role=role,  # Role (User or Admin)
            content=content  # The actual message content
        )
        db_session.add(new_message)  # Add the message to the session
        db_session.commit()  # Commit the changes to the database
    finally:
        db_session.close()  # Close the database session after saving the message


# Check query parameters
query_params = st.query_params

if "admin_id" in query_params and "username" in query_params and "session_id" in query_params:
    admin_id = int(query_params["admin_id"])
    username = query_params["username"]
    session_id = int(query_params["session_id"])

    # Validate admin and session in the database
    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=admin_id, username=username).first()
    session_instance = db_session.query(Session).filter_by(session_id=session_id, admin_id=admin_id).first()
    db_session.close()

    if admin and session_instance:
        st.session_state["session_id"] = session_id

        # Retrieve the messages for this session and load them into session state
        db_session = SessionLocal()
        messages = db_session.query(Message).filter_by(session_id=session_id).order_by(Message.timestamp.asc()).all()
        
        # Load messages into session state
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

# Main content rendering
st.title(f"Welcome, {username}! RAG Deprescribing Chatbot")

# Ensure session_id is set and persistent
db_session = SessionLocal()

if not st.session_state.get("session_id"):
    existing_session = (
        db_session.query(Session)
        .filter_by(admin_id=admin_id)
        .order_by(Session.start_time.desc())
        .first()
    )

    if existing_session:
        st.session_state["session_id"] = existing_session.session_id
    else:
        # Create a new session with a default session name
        default_name = generate_session_name(username)
        new_session = Session(admin_id=admin_id, session_name=default_name)
        db_session.add(new_session)
        db_session.commit()
        st.session_state["session_id"] = new_session.session_id

db_session.close()

# Display session name popover (Renaming functionality)
with st.expander("Session Naming"):
    db_session = SessionLocal()
    current_session = db_session.query(Session).filter_by(session_id=st.session_state["session_id"]).first()

    if current_session:
        st.subheader(f"Current Session: {current_session.session_name}")
        new_session_name = st.text_input("Update session name:", value=current_session.session_name)
        
        if st.button("Save Session Name"):
            current_session.session_name = new_session_name
            db_session.commit()
            st.success("Session name updated!")
    db_session.close()

# Display model selection (always open, no dropdown)
if not st.session_state.get("model_name"):
    st.write("Please choose a model:")
    model_choice = st.radio("Select a model:", options=["GPT", "GEMINI"])

    if st.button("Confirm Model Selection"):
        st.session_state["model_name"] = model_choice.lower()
        st.success(f"Model selected: {model_choice}")

# Set up the model only after selection
if st.session_state.get("model_name"):
    model = setupModel(st.session_state["model_name"])

# Display existing chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle new input from user
if prompt := st.chat_input("Your message:"):
    st.session_state["messages"].append({"role": username, "content": prompt})
    save_message(username, prompt)
    st.chat_message(username).markdown(prompt)

   
    # corn
    st.session_state["current_info"] = retieve_patient_info(prompt, chosen_model, st.session_state["current_info"])
    print("Current Info:", st.session_state["current_info"])
    validation = validate(decision_model, st.session_state["current_info"])
    print(validation)
    if check_score(validation):
        response = generate(st.session_state["current_info"], chosen_model)
        st.chat_message("assistant").markdown(response)
        print("Recommendation:", response)
        st.session_state["messages"].append({"role": "assistant", "content": response})
        save_message("assistant", response)
    else:
        response = get_info(st.session_state["current_info"], chosen_model)
        st.chat_message("assistant").markdown(response)
        print("Response:", response)
        st.session_state["messages"].append({"role": "assistant", "content": response})
        save_message("assistant", response)
