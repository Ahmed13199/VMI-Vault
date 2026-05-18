"""
WSGI entry point for the Flask application.
Use this file to run the application with a WSGI server like Gunicorn.

Example:
    gunicorn wsgi:app
"""
import os
try:
    from reporting_system.app import create_app
except ModuleNotFoundError:
    from app import create_app

# Get configuration from environment or use default
config_name = os.environ.get('FLASK_CONFIG') or 'default'

# Create the application instance
app = create_app(config_name)

if __name__ == '__main__':
    # Run development server
    app.run(host='0.0.0.0', port=5000, debug=True)
