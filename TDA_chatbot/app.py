from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
import os
from Ingestion import Ingestion_file
from Chroma import ChromaManager
from datetime import datetime



app = Flask(__name__)
app.secret_key = "AAA"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.sqlite3'  # Single database for both models
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = 'C://VS_CODES//RAG//Upload'
app.config['ALLOWED_EXTENSIONS'] = {'pdf','csv'}
app.permanent_session_lifetime = timedelta(minutes=5)

db = SQLAlchemy(app)

#class User(db.Model)

class Admin(db.Model):
    _id = db.Column("admin_id", db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)


    def __init__(self, username, email, password, is_admin=False):
        self.username = username
        self.email = email
        self.password = password
        self.is_admin = is_admin

class Resource(db.Model):
    id = db.Column("resource_id", db.Integer, primary_key=True)
    resource_name = db.Column(db.String(100), unique=True)
    resource_type = db.Column(db.String(100))
    supplier_name = db.Column(db.String(100))
    admin_username = db.Column(db.String(100), ForeignKey('admin.username'), nullable=False)  # ForeignKey to the admin_id of Admin model
    admin = db.relationship("Admin", backref="resources")
    created_at = db.Column(db.DateTime, default=datetime.now)


    def __init__(self, resource_name, admin_username, resource_type, supplier_name):
        self.resource_name = resource_name
        self.admin_username = admin_username
        self.resource_type = resource_type
        self.supplier_name = supplier_name

def create_admin():
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(username="admin", email="admin@example.com", password="admin", is_admin=True)
        db.session.add(admin)
        db.session.commit()

@app.route("/home")
@app.route("/")
def home():
    return render_template("index.html", content="hi hi hihi")

@app.route("/view-post", methods=["GET", "POST"])
def view_post():
    if "user" not in session:
        flash("You must be logged in to view posts.")
        return redirect(url_for("login"))
    
    # Fetch all resources
    resources = Resource.query.all()

    current_admin = Admin.query.filter_by(username=session["user"]).first()
    admin_username = current_admin.username if current_admin else "Unknown User"

    if request.method == "POST":
        if "add_resource" in request.form:
            # Adding a new resource
            resource_type = request.form["resource_type"]
            supplier_name = request.form["supplier_name"]
            file = request.files["file"]

            if file and allowed_file(file.filename):
                # Secure the filename and save the file
                filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filename)

                # Check if the file is a PDF or CSV and process accordingly
                if file.filename.lower().endswith('.pdf'):
                    documents = Ingestion_file().chunk_pdf_text(filename)  # Chunking for PDFs
                    if documents:
                        ChromaManager().add_documents(documents)
                        flash(f"Successfully processed and indexed {len(documents)} documents!")
                elif file.filename.lower().endswith('.csv'):
                    documents = Ingestion_file().chunk_csv_text(filename)# Chunking for CSVs
                    if documents:
                        ChromaManager().add_documents(documents)
                        flash(f"Successfully processed and indexed {len(documents)} documents!")
                else:
                    flash("Only PDF and CSV files are allowed.")
                    return redirect(url_for("view_post"))

                # Pass chunks to embedding model and inject into chroma db
                try:
                    flash(f"Successfully processed and indexed {len(documents)} documents!")
                except Exception as e:
                    flash(f"Error processing the file: {e}")
                    return redirect(url_for("view_post"))

                # Add the new resource to the database
                new_resource = Resource(
                    resource_name=file.filename,
                    resource_type=resource_type,
                    supplier_name=supplier_name,
                    admin_username=session["user"]
                )
                db.session.add(new_resource)
                db.session.commit()

                flash("Resource added successfully!")
                return redirect(url_for("view_post"))

        elif "edit_resource" in request.form:
            # Editing an existing resource
            resource_id = request.form["resource_id"]
            resource = Resource.query.get(resource_id)
            if resource:
                resource.resource_type = request.form["resource_type"]
                resource.supplier_name = request.form["supplier_name"]
                db.session.commit()
                flash("Resource updated successfully!")
            else:
                flash("Resource not found.")
            return redirect(url_for("view_post"))

        elif "delete_resource" in request.form:
            # Deleting an existing resource
            resource_id = request.form["resource_id"]
            resource = Resource.query.get(resource_id)
            if resource:
                # Delete the associated file from the upload folder
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], resource.resource_name)
                if os.path.exists(file_path):
                    os.remove(file_path)

                ChromaManager().delete_document(document_id=resource)
                db.session.delete(resource)
                db.session.commit()
                flash("Resource deleted successfully!")
            else:
                flash("Resource not found.")
            return redirect(url_for("view_post"))

    return render_template("view_post.html", resources=resources, admin_username=admin_username)



def allowed_file(filename):
    # Check if the file has an allowed extension (pdf or csv)
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/login", methods=["POST", "GET"])
def login():
    if "user" in session:
        flash("Already Logged In!")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]

        found_user = Admin.query.filter_by(username=user).first()

        if found_user and found_user.password == password:
            if found_user.is_admin:  
                session["user"] = user
                session["email"] = found_user.email
                session["is_admin"] = found_user.is_admin
                flash("Login Successful!")
                return redirect(url_for("home"))
            else:
                flash("Access denied. Only administrators can log in.")
                return redirect(url_for("login"))
        else:
            flash("Login Unsuccessful. Please check your username or password")
            return redirect(url_for("login"))
    
    return render_template("login.html")

@app.route("/user", methods=["POST", "GET"])
def user():
    email = None
    if "user" in session:
        user = session["user"]  # Retrieve username from session

        if request.method == "POST":
            email = request.form["email"]
            session["email"] = email
            found_user = Admin.query.filter_by(username=user).first()
            found_user.email = email
            db.session.commit()
            flash("Email was saved!")
        else:
            if "email" in session:
                email = session["email"]

        return render_template("user.html", email=email, username=user)  # Pass username
    else:
        flash("You are not logged in!")
        return redirect(url_for("login"))

@app.route("/logout")
def logout():
    if "user" in session:
        user = session["user"]
        flash(f"You have been logged out, {user}", "info")
    session.pop("user", None)
    session.pop("email", None)
    return redirect(url_for("login"))

@app.route("/view", methods=["GET", "POST"])
def view():
    if "user" not in session:
        flash("You must be logged in to view users.")
        return redirect(url_for("login"))
    
    if not session.get("is_admin", False):  # Only allow admins to view users
        flash("You do not have permission to view users.")
        return redirect(url_for("user"))
    
    if request.method == "POST":
        user_id = request.form.get("delete_id")
        user_to_delete = Admin.query.get(user_id)
        
        if user_to_delete and user_to_delete.username != "admin":
            db.session.delete(user_to_delete)
            db.session.commit()
            flash(f"User {user_to_delete.username} has been deleted.")
        elif user_to_delete and user_to_delete.username == "admin":
            flash("The master admin cannot be deleted. Nice try. :(")
        else:
            flash("User not found.")
    
    return render_template("view.html", values=Admin.query.all())

@app.route("/add_user", methods=["POST", "GET"])
def add_user():

    if "user" in session and session.get("is_admin", True):
        if request.method == "POST":
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]
            is_admin = "is_admin" in request.form  # Check if checkbox is ticked

            existing_user = Admin.query.filter_by(username=username).first()

            if existing_user:
                flash("User already exists!")
            else:
                new_user = Admin(username=username, email=email, password=password, is_admin=is_admin)
                db.session.add(new_user)
                db.session.commit()
                flash("User added successfully!")

        return render_template("add_user.html")
    else:
        flash("You must be logged in as admin to add users.")
        return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        # Create tables for both Admin and Resource in the same database (app.sqlite3)
        db.create_all()

        create_admin()  # Create the default admin user
    app.run(debug=True)
