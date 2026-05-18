"""
Settings blueprint for metric configuration.
"""
from flask import Blueprint

settings_bp = Blueprint('settings', __name__, template_folder='templates')

from . import routes
