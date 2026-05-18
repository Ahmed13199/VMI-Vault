from flask import Blueprint

journal_bp = Blueprint('journal', __name__, template_folder='templates')

from . import routes
