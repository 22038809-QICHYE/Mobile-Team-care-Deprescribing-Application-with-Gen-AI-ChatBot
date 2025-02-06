import os
import time
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from GenEngine import generate, setupModel, retieve_patient_info, validate, check_score, decision_model, get_info, violation_warning
from promptguard import PromptGuard

# Hide Hamburger Menu and Streamlit Header
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

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
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

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
    feedback = Column(Integer, nullable=True)  # Changed to Integer for star rating
    session = relationship("Session", back_populates="messages")



Base.metadata.create_all(bind=engine)

def generate_response_with_spinner():
    with st.spinner("Generating response for you..."):
        time.sleep(3)  # Simulate processing time
    return "Here is the AI-generated response."

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

if "read_only" in query_params:
    st.session_state["read_only"] = query_params["read_only"].lower() == "true"
else:
    st.session_state["read_only"] = False

if "admin_id" in query_params and "username" in query_params and "session_id" in query_params:
    admin_id = int(query_params["admin_id"])
    username = query_params["username"]
    session_id = int(query_params["session_id"])

    db_session = SessionLocal()
    admin = db_session.query(Admin).filter_by(admin_id=admin_id, username=username).first()
    session_instance = db_session.query(Session).filter_by(session_id=session_id).first()
    db_session.close()

    if admin and session_instance:
        st.session_state["session_id"] = session_id
        st.session_state["read_only"] = admin.admin_id != session_instance.admin_id
        
        db_session = SessionLocal()
        messages = db_session.query(Message).filter_by(session_id=session_id).order_by(Message.timestamp.asc()).all()
        st.session_state["messages"] = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        db_session.close()
    else:
        st.error("Invalid session. Please check the session ID.")
        st.stop()
else:
    st.error("Missing query parameters: admin_id, username, or session_id.")
    st.stop()


# Sidebar settings
if not st.session_state["read_only"]:
    st.sidebar.title("Settings")

    if st.session_state["session_id"]:
        db_session = SessionLocal()
        current_session = db_session.query(Session).filter_by(session_id=st.session_state["session_id"]).first()
        db_session.close()
        
        if current_session:
            st.sidebar.subheader("Session Naming")
            new_session_name = st.sidebar.text_input("Update session name:", value=current_session.session_name)
            if st.sidebar.button("Save Session Name"):
                db_session = SessionLocal()
                current_session = db_session.query(Session).filter_by(session_id=st.session_state["session_id"]).first()

                if current_session:
                    current_session.session_name = new_session_name
                    db_session.commit()
                    st.session_state["session_name"] = new_session_name  # Update session state
                    st.sidebar.success("Session name updated!")
    
                db_session.close()


    st.sidebar.subheader("Model Selection")
    model_choice = st.sidebar.radio("Select a model:", options=["GPT", "GEMINI"], index=0)
    if st.sidebar.button("Confirm Model Selection"):
        st.session_state["model_name"] = model_choice.lower()
        st.sidebar.success(f"Model selected: {model_choice}")

    if st.session_state.get("model_name"):
        model = setupModel(st.session_state["model_name"])
        

# Main content rendering
st.title(f"Welcome, {username}!")

# Display existing chat history
for message in st.session_state["messages"]:
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

# Ensure feedback session state exists
if "feedback" not in st.session_state:
    st.session_state["feedback"] = {}

# Simulate a chat interaction
if not st.session_state["read_only"]:
    if prompt := st.chat_input("Your message:"):
        st.session_state["messages"].append({"role": username, "content": prompt})
        save_message(username, prompt)

        st.markdown(
            f"""
            <div class="chat-row row-reverse">
                <div class="chat-icon">{st.session_state.get("username", username)}</div>
                <div class="chat-bubble human-bubble">{prompt}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Corn (AI Generation Response)
        with st.spinner("Generating response for you..."):
            guard = PromptGuard() 
            is_safe, violations = guard.check_input(prompt)
            if("Prompt injection attempt detected" in violations):
                st.warning("Prompt injection attempt detected. Please try again.")
                st.stop()
            elif not is_safe:
                response = violation_warning(username, prompt, model, violations)
                print("Violation: ", violations)
                print("Response: ", response)
            else:
                st.session_state["current_info"] = retieve_patient_info(prompt, model, st.session_state["current_info"])
                print("Current Info:", st.session_state["current_info"])  # Debugging: Log current info

                validation = validate(decision_model, st.session_state["current_info"])
                print("Validation Result:", validation)  # Debugging: Log validation result

                if check_score(validation):
                    response = generate(st.session_state["current_info"], model)
                    print("Recommendation:", response)  # Debugging: Log AI recommendation
                    st.session_state["current_info"] = "" # Corn
                else:
                    response = get_info(st.session_state["current_info"],prompt, model)
                    print("Response:", response)  # Debugging: Log AI response

        # Display the response after the spinner is done
        st.markdown(
            f"""
            <div class="chat-row">
                <div class="chat-icon">Bot</div>
                <div class="chat-bubble ai-bubble">{response}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Save the AI response in session history
        st.session_state["messages"].append({"role": "assistant", "content": response})
        save_message("assistant", response)

# Unique key for feedback based on number of messages
feedback_key = f"feedback_{len(st.session_state['messages'])}"

# Feedback on AI response (Always visible)
selected = st.feedback("stars", key=feedback_key)

if selected is not None:
    try:
        feedback_value = int(selected) + 1  # Convert to integer (stars are 0-indexed)
        
        # Display different messages based on rating
        if feedback_value <= 3:
            st.markdown("We'll do our best to improve responses")
        else:
            st.markdown("We are happy to be of service to you!")
            
        print(f"User Feedback: {feedback_value} stars")  # Debugging: Ensure feedback is captured

        # Open a new database session
        db_session = SessionLocal()

        # Fetch the last AI-generated message for the session
        last_ai_message = (
            db_session.query(Message)
            .filter_by(session_id=st.session_state["session_id"], role="assistant")
            .order_by(Message.timestamp.desc())
            .first()
        )

        # Debugging: Check if a message was found
        if last_ai_message:
            print("Feedback saved successfully!")
            print(f"Found AI message with ID: {last_ai_message.message_id}")  # Debugging
            last_ai_message.feedback = feedback_value  # Update feedback column
            db_session.commit()
        else:
            print("No AI message found.")  # Debugging
            st.error("No AI response found to attach feedback.")

        db_session.close()

    except Exception as e:
        st.error(f"Error saving feedback: {e}")
        print(f"Error saving feedback: {e}")  # Debugging

# Read-only mode warning if applicable
if st.session_state["read_only"]:
    st.warning("Read-only mode: You can view chat history but cannot send messages.")

