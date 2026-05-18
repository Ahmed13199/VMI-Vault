from flask import Blueprint

sales_team_bp = Blueprint('sales_team', __name__, template_folder='templates')

from . import routes
