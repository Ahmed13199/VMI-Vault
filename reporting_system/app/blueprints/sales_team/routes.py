import uuid

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from . import sales_team_bp
from ...extensions import db
from ...models.sales_team import (
    SalesGuidelinePartition,
    SalesGuidelineResource,
    SalesGuidelineSection,
    SalesGuidelineSubsection,
)
from ...models.team import Team
from ...permissions import require_page_permission
from ...services.r2_service import R2Service


def _next_position(model, **filters):
    query = db.session.query(db.func.max(model.position))
    for key, value in filters.items():
        query = query.filter(getattr(model, key) == value)
    current = query.scalar() or 0
    return current + 1


def _default_team_id():
    if getattr(current_user, 'team_id', None):
        return current_user.team_id

    sales_team = Team.query.filter(db.func.lower(Team.name) == 'sales').first()
    if sales_team:
        return sales_team.id

    first_team = Team.query.order_by(Team.name.asc()).first()
    return first_team.id if first_team else None


def _selected_team():
    teams = Team.query.order_by(Team.name.asc()).all()
    if not teams:
        abort(404)

    requested_team_id = request.args.get('team', type=int)
    fallback_team_id = _default_team_id()
    valid_team_ids = {team.id for team in teams}
    team_id = requested_team_id if requested_team_id in valid_team_ids else fallback_team_id
    if team_id not in valid_team_ids:
        team_id = teams[0].id

    team_obj = next(team for team in teams if team.id == team_id)
    return team_obj, teams


def _can_manage_team(team_id: int) -> bool:
    if getattr(current_user, 'is_admin', lambda: False)():
        return True
    return getattr(current_user, 'team_id', None) == team_id


def _ensure_team_editor(team_id: int):
    if _can_manage_team(team_id):
        return None
    flash('You can only edit the knowledge base for your own team.', 'error')
    return redirect(url_for('sales_team.guidelines', team=team_id))


def _count_resources(partitions):
    return sum(len(partition.resources) for partition in partitions) + sum(
        len(section.resources) + sum(len(subsection.resources) for subsection in section.subsections)
        for partition in partitions
        for section in partition.sections
    )


def _guidelines_context(team_obj: Team, teams: list[Team]):
    partitions = (
        SalesGuidelinePartition.query
        .filter(SalesGuidelinePartition.team_id == team_obj.id)
        .order_by(SalesGuidelinePartition.position.asc(), SalesGuidelinePartition.created_at.asc())
        .all()
    )

    total_sections = sum(len(partition.sections) for partition in partitions)
    total_subsections = sum(len(section.subsections) for partition in partitions for section in partition.sections)
    total_resources = _count_resources(partitions)

    return {
        'active_tab': 'guidelines',
        'teams': teams,
        'selected_team': team_obj,
        'partitions': partitions,
        'can_manage_selected_team': _can_manage_team(team_obj.id) and current_user.can_edit_page('sales_team'),
        'stats': {
            'partitions': len(partitions),
            'sections': total_sections,
            'subsections': total_subsections,
            'resources': total_resources,
        },
    }


def _resource_parent(level: str, parent_id: int):
    if level == 'partition':
        parent = SalesGuidelinePartition.query.get_or_404(parent_id)
        return parent, parent.team_id, {'partition_id': parent.id}
    if level == 'section':
        parent = SalesGuidelineSection.query.get_or_404(parent_id)
        return parent, parent.partition.team_id, {'section_id': parent.id}
    if level == 'subsection':
        parent = SalesGuidelineSubsection.query.get_or_404(parent_id)
        return parent, parent.section.partition.team_id, {'subsection_id': parent.id}
    abort(404)


def _upload_storage_key(team_name: str, filename: str):
    team_slug = (team_name or 'team').strip().lower().replace(' ', '-')
    return f"team-guidelines/{team_slug}/{uuid.uuid4().hex}_{filename}"


@sales_team_bp.route('/')
@login_required
@require_page_permission('sales_team')
def index():
    team_obj, _ = _selected_team()
    return redirect(url_for('sales_team.guidelines', team=team_obj.id))


@sales_team_bp.route('/guidelines')
@login_required
@require_page_permission('sales_team')
def guidelines():
    team_obj, teams = _selected_team()
    return render_template('sales_team/index.html', **_guidelines_context(team_obj, teams))


@sales_team_bp.route('/guidelines/partitions/new', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def create_partition():
    team_id = request.form.get('team_id', type=int)
    team_obj = Team.query.get_or_404(team_id)

    denied = _ensure_team_editor(team_obj.id)
    if denied is not None:
        return denied

    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip() or None

    if not title:
        flash('Section group title is required.', 'error')
        return redirect(url_for('sales_team.guidelines', team=team_obj.id))

    partition = SalesGuidelinePartition(
        team_id=team_obj.id,
        title=title,
        description=description,
        position=_next_position(SalesGuidelinePartition, team_id=team_obj.id),
        created_by_user_id=getattr(current_user, 'id', None),
    )
    db.session.add(partition)
    db.session.commit()

    flash('Section group created.', 'success')
    return redirect(url_for('sales_team.guidelines', team=team_obj.id))


@sales_team_bp.route('/guidelines/partitions/<int:partition_id>/delete', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def delete_partition(partition_id: int):
    partition = SalesGuidelinePartition.query.get_or_404(partition_id)

    denied = _ensure_team_editor(partition.team_id)
    if denied is not None:
        return denied

    db.session.delete(partition)
    db.session.commit()
    flash('Section group deleted.', 'success')
    return redirect(url_for('sales_team.guidelines', team=partition.team_id))


@sales_team_bp.route('/guidelines/partitions/<int:partition_id>/sections/new', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def create_section(partition_id: int):
    partition = SalesGuidelinePartition.query.get_or_404(partition_id)

    denied = _ensure_team_editor(partition.team_id)
    if denied is not None:
        return denied

    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip() or None

    if not title:
        flash('Section title is required.', 'error')
        return redirect(url_for('sales_team.guidelines', team=partition.team_id))

    section = SalesGuidelineSection(
        partition_id=partition.id,
        title=title,
        description=description,
        position=_next_position(SalesGuidelineSection, partition_id=partition.id),
        created_by_user_id=getattr(current_user, 'id', None),
    )
    db.session.add(section)
    db.session.commit()

    flash('Section created.', 'success')
    return redirect(url_for('sales_team.guidelines', team=partition.team_id))


@sales_team_bp.route('/guidelines/sections/<int:section_id>/delete', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def delete_section(section_id: int):
    section = SalesGuidelineSection.query.get_or_404(section_id)
    team_id = section.partition.team_id

    denied = _ensure_team_editor(team_id)
    if denied is not None:
        return denied

    db.session.delete(section)
    db.session.commit()
    flash('Section deleted.', 'success')
    return redirect(url_for('sales_team.guidelines', team=team_id))


@sales_team_bp.route('/guidelines/sections/<int:section_id>/subsections/new', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def create_subsection(section_id: int):
    section = SalesGuidelineSection.query.get_or_404(section_id)
    team_id = section.partition.team_id

    denied = _ensure_team_editor(team_id)
    if denied is not None:
        return denied

    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip() or None

    if not title:
        flash('Subsection title is required.', 'error')
        return redirect(url_for('sales_team.guidelines', team=team_id))

    subsection = SalesGuidelineSubsection(
        section_id=section.id,
        title=title,
        description=description,
        position=_next_position(SalesGuidelineSubsection, section_id=section.id),
        created_by_user_id=getattr(current_user, 'id', None),
    )
    db.session.add(subsection)
    db.session.commit()

    flash('Subsection created.', 'success')
    return redirect(url_for('sales_team.guidelines', team=team_id))


@sales_team_bp.route('/guidelines/subsections/<int:subsection_id>/delete', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def delete_subsection(subsection_id: int):
    subsection = SalesGuidelineSubsection.query.get_or_404(subsection_id)
    team_id = subsection.section.partition.team_id

    denied = _ensure_team_editor(team_id)
    if denied is not None:
        return denied

    db.session.delete(subsection)
    db.session.commit()
    flash('Subsection deleted.', 'success')
    return redirect(url_for('sales_team.guidelines', team=team_id))


@sales_team_bp.route('/guidelines/<string:level>/<int:parent_id>/resources/new', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def create_resource(level: str, parent_id: int):
    parent, team_id, parent_fields = _resource_parent(level, parent_id)

    denied = _ensure_team_editor(team_id)
    if denied is not None:
        return denied

    title = (request.form.get('title') or '').strip()
    link_url = (request.form.get('url') or '').strip()
    file = request.files.get('file')

    if not link_url and (not file or not file.filename):
        flash('Add either a file or a URL.', 'error')
        return redirect(url_for('sales_team.guidelines', team=team_id))

    if link_url and file and file.filename:
        flash('Please add either a file or a URL, not both at once.', 'error')
        return redirect(url_for('sales_team.guidelines', team=team_id))

    if link_url:
        if not (link_url.startswith('http://') or link_url.startswith('https://')):
            flash('URL must start with http:// or https://', 'error')
            return redirect(url_for('sales_team.guidelines', team=team_id))

        if not title:
            title = link_url

        resource = SalesGuidelineResource(
            title=title,
            resource_type='link',
            url=link_url,
            created_by_user_id=getattr(current_user, 'id', None),
            **parent_fields,
        )
        db.session.add(resource)
        db.session.commit()
        flash('Link added.', 'success')
        return redirect(url_for('sales_team.guidelines', team=team_id))

    original_filename = secure_filename(file.filename)
    if not original_filename:
        flash('Invalid file name.', 'error')
        return redirect(url_for('sales_team.guidelines', team=team_id))

    if not title:
        title = original_filename

    team_name = parent.team.name if hasattr(parent, 'team') else parent.partition.team.name if hasattr(parent, 'partition') else parent.section.partition.team.name
    key = _upload_storage_key(team_name, original_filename)
    content_type = getattr(file, 'mimetype', None)
    R2Service.upload_fileobj(file, key, content_type=content_type)

    size_bytes = None
    try:
        size_bytes = file.content_length
    except Exception:
        size_bytes = None

    resource = SalesGuidelineResource(
        title=title,
        resource_type='file',
        storage_key=key,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        created_by_user_id=getattr(current_user, 'id', None),
        **parent_fields,
    )
    db.session.add(resource)
    db.session.commit()

    flash('File uploaded.', 'success')
    return redirect(url_for('sales_team.guidelines', team=team_id))


@sales_team_bp.route('/guidelines/resources/<int:resource_id>/open')
@login_required
@require_page_permission('sales_team')
def open_resource(resource_id: int):
    resource = SalesGuidelineResource.query.get_or_404(resource_id)
    team_id = resource.owner_team_id

    if resource.resource_type == 'link' and resource.url:
        return redirect(resource.url)
    if resource.resource_type == 'file' and resource.storage_key:
        return redirect(R2Service.presigned_get_url(resource.storage_key, expires_in_seconds=600))

    flash('Resource is not available.', 'error')
    return redirect(url_for('sales_team.guidelines', team=team_id))


@sales_team_bp.route('/guidelines/resources/<int:resource_id>/delete', methods=['POST'])
@login_required
@require_page_permission('sales_team', 'edit')
def delete_resource(resource_id: int):
    resource = SalesGuidelineResource.query.get_or_404(resource_id)
    team_id = resource.owner_team_id

    denied = _ensure_team_editor(team_id)
    if denied is not None:
        return denied

    if resource.resource_type == 'file' and resource.storage_key:
        try:
            R2Service.delete_object(resource.storage_key)
        except Exception:
            pass

    db.session.delete(resource)
    db.session.commit()
    flash('Resource deleted.', 'success')
    return redirect(url_for('sales_team.guidelines', team=team_id))
