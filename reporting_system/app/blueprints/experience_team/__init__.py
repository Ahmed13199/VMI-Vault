from flask import Blueprint

experience_team_bp = Blueprint('experience_team', __name__, template_folder='templates')

from . import routes
