"""
Application factory for the Flask reporting system.
"""
from flask import Flask, redirect, url_for
from .extensions import db, migrate, login_manager
from .config import config


def create_app(config_name='default'):
    """
    Application factory function.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing', 'default')
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader callback
    from .models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.team_processes import team_processes_bp
    from .blueprints.documents import documents_bp
    from .blueprints.framework import framework_bp
    from .blueprints.journal import journal_bp
    from .blueprints.experience_team import experience_team_bp
    from .blueprints.sales_team import sales_team_bp
    from .blueprints.settings import settings_bp
    from .blueprints.reporting import reporting_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(team_processes_bp, url_prefix='/team-processes')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(framework_bp, url_prefix='/framework')
    app.register_blueprint(journal_bp, url_prefix='/journal')
    app.register_blueprint(experience_team_bp, url_prefix='/experience-team')
    app.register_blueprint(sales_team_bp, url_prefix='/sales-team')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(reporting_bp, url_prefix='/reporting')
    
    # Root route redirect
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))
    
    # Context processor for templates
    @app.context_processor
    def inject_globals():
        from .models.team import Team
        from .services.access_service import AccessService
        return {
            'teams': Team.query.all(),
            'access_pages': AccessService.PAGE_DEFINITIONS,
        }
    
    return app
