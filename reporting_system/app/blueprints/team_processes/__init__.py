from flask import Blueprint

team_processes_bp = Blueprint('team_processes', __name__, template_folder='templates')

from . import routes
