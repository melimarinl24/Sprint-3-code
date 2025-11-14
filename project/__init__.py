# project/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv

# ==========================================================
#  Initialize extensions
# ==========================================================
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

# ==========================================================
#  Application Factory
# ==========================================================
def create_app():
    app = Flask(__name__)

    # --------------------------
    # Load environment variables
    # --------------------------
    load_dotenv()

    # --------------------------
    # Basic Config
    # --------------------------
    
    # ...
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")

    app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST", "127.0.0.1")
    app.config['MYSQL_USER'] = os.getenv("MYSQL_USER", "root")
    app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD", "")
    app.config['MYSQL_DB'] = os.getenv("MYSQL_DB", "er_system")

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{app.config['MYSQL_USER']}:{app.config['MYSQL_PASSWORD']}"
        f"@{app.config['MYSQL_HOST']}/{app.config['MYSQL_DB']}?charset=utf8mb4"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # ...

    # --------------------------
    # Initialize extensions
    # --------------------------
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # --------------------------
    # Login manager setup
    # --------------------------
    from .models import User  # Import here to avoid circular imports

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --------------------------
    # Create database tables
    # --------------------------
    with app.app_context():
        db.create_all()

    # --------------------------
    # Register Blueprints (active)
    # --------------------------
    from .views import bp as main
    from .auth import auth
    from .student_ui import student_ui 
    print("📘 Imported student_ui =", student_ui)

    from .faculty_ui import faculty_ui

    print("✅ Registering blueprints...")

    app.register_blueprint(main)
    print("✅ main registered")

    app.register_blueprint(auth)
    print("✅ auth registered")

    app.register_blueprint(student_ui)
    print("📘 Blueprint names after register =", app.blueprints.keys())

    app.register_blueprint(faculty_ui, url_prefix="/faculty")
    print("✅ faculty_ui registered")

    

    # Old student_exam_routes blueprint is now deprecated.
    # All student-facing functionality has been moved to student_ui.py.

    # --------------------------
    # CLI Context (optional)
    # --------------------------
    @app.shell_context_processor
    def make_shell_context():
        return {"db": db, "User": User}
    

    

    return app
