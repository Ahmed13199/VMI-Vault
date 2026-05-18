"""
Reporting blueprint for data entry and output.
"""
from flask import Blueprint

reporting_bp = Blueprint('reporting', __name__, template_folder='templates')

from . import routes
