"""
Flask extensions initialization.
Extensions are initialized here without the app instance,
then bound to the app in the application factory.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Database ORM
db = SQLAlchemy()

# Database migrations
migrate = Migrate()

# Login manager for session-based authentication
login_manager = LoginManager()
