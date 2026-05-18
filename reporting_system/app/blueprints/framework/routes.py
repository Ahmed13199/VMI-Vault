from flask import render_template
from flask_login import login_required

from . import framework_bp
from ...models.document_folder import DocumentFolder
from ...models.team import Team
from ...models.team_process import TeamProcess
from ...permissions import require_page_permission


@framework_bp.route('/')
@login_required
@require_page_permission('framework')
def index():
    folders = (DocumentFolder.query
               .filter(DocumentFolder.parent_id.is_(None))
               .order_by(DocumentFolder.name.asc())
               .all())

    teams = Team.query.order_by(Team.name.asc()).all()
    processes = TeamProcess.query.order_by(TeamProcess.updated_at.desc()).all()

    by_team = {}
    for p in processes:
        by_team.setdefault(p.team_id, []).append(p)

    return render_template('framework/index.html', folders=folders, teams=teams, by_team=by_team)
