import streamlit as st
from chatbotapp import username, admin_id
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from inte5cz import generate, setupModel  # Import functions from inte3.py

# Database setup
DATABASE_URL =  "sqlite:///app.sqlite3"
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

# Database models
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
        print(f"Welcome, {admin.username}! Session ID: {session_id}")
        st.session_state["session_id"] = session_id
    else:
        st.error("Invalid admin or session. Please log in.")
        st.stop()
else:
    st.error("Missing query parameters: admin_id, username, or session_id.")
    st.stop()


st.title(f"Welcome, {username}! C300 AI Chat Bot")

# Ensure session_id is set and persistent
db_session = SessionLocal()

# Check if there is already a session_id in st.session_state
if not st.session_state.get("session_id"):
    # Fetch the latest session for the admin
    existing_session = (
        db_session.query(Session)
        .filter_by(admin_id=admin_id)
        .order_by(Session.start_time.desc())
        .first()
    )

    if existing_session:
        # Use the latest session for the admin
        st.session_state["session_id"] = existing_session.session_id
    else:
        # Create a new session if none exists
        new_session = Session(admin_id=admin_id)
        db_session.add(new_session)
        db_session.commit()
        st.session_state["session_id"] = new_session.session_id

db_session.close()




# Load chat history only for the current session
if not st.session_state["messages"]:
    db_session = SessionLocal()
    messages = (
        db_session.query(Message)
        .filter_by(session_id=st.session_state["session_id"])
        .order_by(Message.timestamp.asc())
        .all()
    )
    for msg in messages:
        st.session_state["messages"].append({"role": msg.role, "content": msg.content})
    db_session.close()


# Save messages
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






# Display existing chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Model selection
if not st.session_state.get("model_name"):
    st.write("Please choose a model:")
    st.write("1. GPT")
    st.write("2. GEMINI")
    admin_input = st.text_input("Type '1' for GPT or '2' for GEMINI:")

    if admin_input:
        if admin_input.strip() == "1":
            st.session_state["model_name"] = "gpt"
        elif admin_input.strip() == "2":
            st.session_state["model_name"] = "gemini"
        else:
            st.error("Invalid choice. Please type '1' or '2'.")
        
        if st.session_state["model_name"]:
            # Add the model selection to chat history
            model_selection_message = f"Model selected: {st.session_state['model_name']}"
            st.session_state["messages"].append({
                "role": "system",
                "content": model_selection_message
            })
            st.chat_message("system").markdown(model_selection_message)

# Set up the model only after selection
if st.session_state.get("model_name"):
    model = setupModel(st.session_state["model_name"])

# Handle new input from admin
if prompt := st.chat_input("Your message:"):
    # Add admin input to chat history
    st.session_state["messages"].append({"role": "admin", "content": prompt})
    save_message("admin", prompt)
    st.chat_message("admin").markdown(prompt)

    # Validate and generate a response
    response = generate(prompt, model , st.session_state["messages"])
    
    # Add the response to chat history
    st.session_state["messages"].append({"role": "assistant", "content": response})
    save_message("assistant", response)
    st.chat_message("assistant").markdown(response)

