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
app.config['UPLOAD_FOLDER'] = "D:/SCHOOL WORK/FYP INTEGRATED/Mobile-Team-care-Deprescribing-Application-with-Gen-AI-ChatBot-main/Upload"
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
    admin_id = db.Column(db.Integer, ForeignKey('admin.admin_id'), nullable=False) 
    resource_name = db.Column(db.String(100), unique=True)
    resource_type = db.Column(db.String(100))
    supplier_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    admin = db.relationship("Admin", backref="resources")
    


    def __init__(self, resource_name, admin_id, resource_type, supplier_name):
        self.resource_name = resource_name
        self.admin_id = admin_id
        self.resource_type = resource_type
        self.supplier_name = supplier_name

class AuditLog(db.Model):
    admin_log_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, ForeignKey('admin.admin_id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    admin = db.relationship("Admin", backref="audit_logs")

    def __init__(self, admin_id, action):
        self.admin_id = admin_id
        self.action = action


def create_admin():
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(username="admin", email="admin@example.com", password="admin", is_admin=True)
        db.session.add(admin)
        db.session.commit()

def file_exists(filename):
    return os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route("/home")
@app.route("/")
def home():
    return render_template("index.html", content="TDA Chatbot's Admin Site")




#VIEW, EDIT, AND DELETE RESOURCES
@app.route("/view-post", methods=["GET", "POST"])
def view_post():
    if "user" not in session:
        flash("You must be logged in to view posts.")
        return redirect(url_for("login"))
    
    # Fetch all resources
    resources = Resource.query.all()

    current_admin = Admin.query.filter_by(username=session["user"]).first()

    if request.method == "POST":

        admin_id = current_admin._id

    if "add_resource" in request.form:
        # Adding a new resource
        resource_type = request.form["resource_type"]
        supplier_name = request.form["supplier_name"]
        file = request.files["file"]

        if file and allowed_file(file.filename):
            # Secure the filename and check if it already exists
            filename = file.filename

            if file_exists(filename):
                flash(f"File '{filename}' already exists. Please confirm if it is the correct file. ")
                flash(f"Otherwise delete the existing file and re-upload file with latest changes. ")
                return redirect(url_for("view_post"))
            
            # Save the file if it doesn't exist
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            if filename.lower().endswith('.pdf'):
                documents = Ingestion_file().chunk_pdf_text(file_path)
                if documents:
                    ChromaManager().add_documents(documents)
                    flash(f"Processed and indexed {len(documents)} documents!")
            elif filename.lower().endswith('.csv'):
                documents = Ingestion_file().chunk_csv_text(file_path)
                if documents:
                    ChromaManager().add_documents(documents)
                    flash(f"Processed and indexed {len(documents)} documents!")
            else:
                flash("Only PDF and CSV files are allowed.")
                return redirect(url_for("view_post"))

            new_resource = Resource(
                resource_name=filename,
                admin_id=admin_id,
                resource_type=resource_type,
                supplier_name=supplier_name
            )
            db.session.add(new_resource)

            action = f"{session['user']} has added '{filename}'"
            
            if db.session.query(AuditLog).count() >= 20:
                oldest_log = AuditLog.query.order_by(AuditLog.timestamp).first()
                db.session.delete(oldest_log)

            db.session.add(AuditLog(admin_id=admin_id, action=action))
            db.session.commit()

            flash("Resource added successfully!")
            return redirect(url_for("view_post"))

    elif "edit_resource" in request.form:
        # Editing an existing resource
        resource_id = request.form["resource_id"]
        resource = Resource.query.get(resource_id)

        if resource:
            old_resource_type = resource.resource_type
            old_supplier_name = resource.supplier_name

            
            resource.resource_type = request.form["resource_type"]
            resource.supplier_name = request.form["supplier_name"]
            db.session.commit()

            action = f"{session['user']} has edited resource '{resource.resource_name}'"

            if old_resource_type != resource.resource_type:
                action += f", changed resource type from '{old_resource_type}' to '{resource.resource_type}'"
            if old_supplier_name != resource.supplier_name:
                action += f", changed supplier name from '{old_supplier_name}' to '{resource.supplier_name}'"

            if db.session.query(AuditLog).count() >= 20:
                oldest_log = AuditLog.query.order_by(AuditLog.timestamp).first()
                db.session.delete(oldest_log)

            db.session.add(AuditLog(admin_id=admin_id, action=action))
            db.session.commit()

            flash("Resource updated successfully!")
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

            print(file_path)
            ChromaManager().delete_documents_by_metadata_source(source_value=file_path)
            db.session.delete(resource)
            db.session.commit()

            
            action = f"{session['user']} has deleted '{resource.resource_name}'"

            if db.session.query(AuditLog).count() >= 20:
                oldest_log = AuditLog.query.order_by(AuditLog.timestamp).first()
                db.session.delete(oldest_log)

            db.session.add(AuditLog(admin_id=admin_id, action=action))
            db.session.commit()

            flash("Resource deleted successfully!")
            return redirect(url_for("view_post"))

    return render_template("view_post.html", resources=resources)



def allowed_file(filename):
    # Check if the file has an allowed extension (pdf or csv)
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


#LOGIN
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


#VIEW AND DELETE USERS
@app.route("/view", methods=["GET", "POST"])
def view():
    if "user" not in session:
        flash("You must be logged in to view users.")
        return redirect(url_for("login"))
    
    if not session.get("is_admin", False): 
        flash("You do not have permission to view users.")
        return redirect(url_for("user"))
    
    if request.method == "POST":
        user_id = request.form.get("delete_id")
        user_to_delete = Admin.query.get(user_id)
        
        if user_to_delete:

            if user_to_delete.username == "admin":
                flash("The master admin cannot be deleted.")

                action = f"Attempted to delete the master admin."
                db.session.add(AuditLog(admin_id=Admin.query.filter_by(username=session['user']).first()._id, action=action))
                db.session.commit()
            else:

                db.session.delete(user_to_delete)
                db.session.commit()
                flash(f"User {user_to_delete.username} has been deleted.")
                

                action = f"{session['user']} has deleted {user_to_delete.username} ({'Admin' if user_to_delete.is_admin else 'User'})."
                db.session.add(AuditLog(admin_id=Admin.query.filter_by(username=session['user']).first()._id, action=action))
                db.session.commit()
        else:
            flash("User not found.")
    
    return render_template("view.html", values=Admin.query.all())


#ADD USERS
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

                # Log the creation of the new user
                action = f"{session['user']} has created {username} ({'Admin' if is_admin else 'User'})."
                db.session.add(AuditLog(admin_id=Admin.query.filter_by(username=session['user']).first()._id, action=action))
                db.session.commit()

        return render_template("add_user.html")
    else:
        flash("You must be logged in as admin to add users.")
        return redirect(url_for("login"))
    
@app.route("/audit-log")
def audit_log():
    if "user" not in session:
        flash("You must be logged in to view the audit log.")
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        flash("You do not have permission to view the audit log.")
        return redirect(url_for("home"))

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template("admin_audit_log.html", logs=logs)

if __name__ == "__main__":
    with app.app_context():
        # Create tables for both Admin and Resource in the same database (app.sqlite3)
        db.create_all()

        create_admin()  # Create the default admin user
    app.run(debug=False)
