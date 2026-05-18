from flask import Blueprint

framework_bp = Blueprint('framework', __name__, template_folder='templates')

from . import routes
