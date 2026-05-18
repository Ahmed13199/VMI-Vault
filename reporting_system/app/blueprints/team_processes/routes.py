from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import bleach

try:
    from bleach.css_sanitizer import CSSSanitizer
except Exception:
    CSSSanitizer = None

from . import team_processes_bp
from ...extensions import db
from ...models.team import Team
from ...models.team_process import TeamProcess, TeamProcessSection
from ...permissions import require_page_permission


def _slugify(value: str) -> str:
    value = (value or '').strip().lower()
    value = value.replace(' ', '-')
    value = ''.join(ch for ch in value if ch.isalnum() or ch in ('-', '_'))
    value = value.strip('-_')
    return value or 'process'


def _can_edit_process(user, process: TeamProcess) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_admin', lambda: False)():
        return True
    if process.created_by_user_id is None:
        return getattr(user, 'team_id', None) == process.team_id
    return process.created_by_user_id == user.id


def _can_edit_section(user, process: TeamProcess, section: TeamProcessSection) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_admin', lambda: False)():
        return True
    if section.created_by_user_id is None:
        return getattr(user, 'team_id', None) == process.team_id
    if section.created_by_user_id == user.id:
        return True
    if process.created_by_user_id is None:
        return getattr(user, 'team_id', None) == process.team_id
    return process.created_by_user_id == user.id


def _sanitize_html(html: str | None) -> str | None:
    if html is None:
        return None
    allowed_tags = [
        'p', 'br', 'div', 'span',
        'font',
        'strong', 'b', 'em', 'i', 'u', 's',
        'ul', 'ol', 'li',
        'blockquote',
        'h2', 'h3', 'h4',
        'a'
    ]
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel']
    }

    css_sanitizer = None
    if CSSSanitizer is not None:
        allowed_attributes['*'] = ['style']
        allowed_attributes['font'] = ['style', 'color']
        css_sanitizer = CSSSanitizer(
            allowed_css_properties=[
                'color',
                'background-color',
                'font-size',
                'font-style',
                'font-weight',
                'text-decoration',
                'text-align'
            ]
        )
    else:
        allowed_attributes['font'] = ['color']

    cleaned = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=['http', 'https', 'mailto'],
        strip=True,
        css_sanitizer=css_sanitizer
    )
    cleaned = cleaned.strip() or None
    return cleaned


def _sanitize_title_html(html: str | None) -> str | None:
    if html is None:
        return None
    allowed_tags = [
        'br', 'span', 'div',
        'font',
        'strong', 'b', 'em', 'i', 'u', 's'
    ]
    allowed_attributes = {}
    css_sanitizer = None
    if CSSSanitizer is not None:
        allowed_attributes['*'] = ['style']
        allowed_attributes['font'] = ['style', 'color']
        css_sanitizer = CSSSanitizer(
            allowed_css_properties=[
                'color',
                'background-color',
                'font-size',
                'font-style',
                'font-weight',
                'text-decoration',
                'text-align'
            ]
        )
    else:
        allowed_attributes['font'] = ['color']

    cleaned = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=['http', 'https', 'mailto'],
        strip=True,
        css_sanitizer=css_sanitizer
    )
    cleaned = cleaned.strip() or None
    return cleaned


@team_processes_bp.route('/')
@login_required
@require_page_permission('team_processes')
def index():
    teams = Team.query.order_by(Team.name.asc()).all()
    processes = TeamProcess.query.order_by(TeamProcess.updated_at.desc()).all()

    by_team = {}
    for p in processes:
        by_team.setdefault(p.team_id, []).append(p)

    return render_template('team_processes/index.html', teams=teams, by_team=by_team)


@team_processes_bp.route('/team/<int:team_id>')
@login_required
@require_page_permission('team_processes')
def team(team_id: int):
    team_obj = Team.query.get_or_404(team_id)

    processes = (TeamProcess.query
                 .filter(TeamProcess.team_id == team_obj.id)
                 .order_by(TeamProcess.updated_at.desc())
                 .all())

    return render_template('team_processes/team.html', team=team_obj, processes=processes)


@team_processes_bp.route('/team/<int:team_id>/new', methods=['GET', 'POST'])
@login_required
@require_page_permission('team_processes', 'edit')
def create_process(team_id: int):
    team_obj = Team.query.get_or_404(team_id)

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        status = (request.form.get('status') or 'draft').strip()
        slug = (request.form.get('slug') or '').strip()

        if not title:
            flash('Title is required.', 'error')
            return render_template('team_processes/process_form.html', team=team_obj, process=None, form_data=request.form)

        slug = _slugify(slug or title)

        existing = TeamProcess.query.filter_by(team_id=team_obj.id, slug=slug).first()
        if existing:
            flash('A process with this slug already exists for this team.', 'error')
            return render_template('team_processes/process_form.html', team=team_obj, process=None, form_data=request.form)

        process = TeamProcess(team_id=team_obj.id, title=title, slug=slug, status=status, created_by_user_id=current_user.id)
        db.session.add(process)
        db.session.commit()

        flash('Process created.', 'success')
        return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))

    return render_template('team_processes/process_form.html', team=team_obj, process=None, form_data={})


@team_processes_bp.route('/team/<int:team_id>/process/<int:process_id>')
@login_required
@require_page_permission('team_processes')
def view_process(team_id: int, process_id: int):
    team_obj = Team.query.get_or_404(team_id)
    process = TeamProcess.query.filter_by(id=process_id, team_id=team_obj.id).first_or_404()

    return render_template('team_processes/process_view.html', team=team_obj, process=process)


@team_processes_bp.route('/team/<int:team_id>/process/<int:process_id>/edit', methods=['GET', 'POST'])
@login_required
@require_page_permission('team_processes', 'edit')
def edit_process(team_id: int, process_id: int):
    team_obj = Team.query.get_or_404(team_id)
    process = TeamProcess.query.filter_by(id=process_id, team_id=team_obj.id).first_or_404()

    if not _can_edit_process(current_user, process):
        flash('Only the creator can edit this process.', 'error')
        return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))

    if process.created_by_user_id is None:
        process.created_by_user_id = current_user.id
        db.session.commit()

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        status = (request.form.get('status') or 'draft').strip()
        slug = (request.form.get('slug') or '').strip()

        if not title:
            flash('Title is required.', 'error')
            return render_template('team_processes/process_form.html', team=team_obj, process=process, form_data=request.form)

        slug = _slugify(slug or title)

        existing = TeamProcess.query.filter_by(team_id=team_obj.id, slug=slug).first()
        if existing and existing.id != process.id:
            flash('A process with this slug already exists for this team.', 'error')
            return render_template('team_processes/process_form.html', team=team_obj, process=process, form_data=request.form)

        process.title = title
        process.status = status
        process.slug = slug
        db.session.commit()

        flash('Process updated.', 'success')
        return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))

    return render_template('team_processes/process_form.html', team=team_obj, process=process, form_data={
        'title': process.title,
        'slug': process.slug,
        'status': process.status,
    })


@team_processes_bp.route('/team/<int:team_id>/process/<int:process_id>/delete', methods=['POST'])
@login_required
@require_page_permission('team_processes', 'edit')
def delete_process(team_id: int, process_id: int):
    team_obj = Team.query.get_or_404(team_id)
    process = TeamProcess.query.filter_by(id=process_id, team_id=team_obj.id).first_or_404()

    if not _can_edit_process(current_user, process):
        flash('Only the creator can delete this process.', 'error')
        return redirect(url_for('team_processes.view_process', team_id=team_id, process_id=process_id))

    db.session.delete(process)
    db.session.commit()

    flash('Process deleted.', 'success')
    return redirect(url_for('team_processes.team', team_id=team_obj.id))


@team_processes_bp.route('/team/<int:team_id>/process/<int:process_id>/sections/new', methods=['POST'])
@login_required
@require_page_permission('team_processes', 'edit')
def add_section(team_id: int, process_id: int):
    team_obj = Team.query.get_or_404(team_id)
    process = TeamProcess.query.filter_by(id=process_id, team_id=team_obj.id).first_or_404()

    if not _can_edit_process(current_user, process):
        flash('Only the creator can add sections to this process.', 'error')
        return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))

    if process.created_by_user_id is None:
        process.created_by_user_id = current_user.id
        db.session.commit()

    section_type = (request.form.get('section_type') or 'paragraph').strip()
    text_align = (request.form.get('text_align') or 'left').strip().lower()
    title = (request.form.get('title') or '').strip() or None
    title_html = (request.form.get('title_html') or '').strip() or None
    raw_content = (request.form.get('content') or '').strip() or None
    raw_content_html = (request.form.get('content_html') or '').strip() or None

    if raw_content_html is not None:
        content = _sanitize_html(raw_content_html)
    else:
        content = _sanitize_html(raw_content)

    title_html = _sanitize_title_html(title_html)

    if text_align not in ('left', 'center', 'right'):
        text_align = 'left'

    max_pos = db.session.query(db.func.max(TeamProcessSection.position)).filter(TeamProcessSection.process_id == process.id).scalar()
    next_pos = (max_pos or 0) + 1

    section = TeamProcessSection(
        process_id=process.id,
        position=next_pos,
        section_type=section_type,
        text_align=text_align,
        title=title,
        title_html=title_html,
        content=content,
        created_by_user_id=current_user.id,
    )

    db.session.add(section)
    db.session.commit()

    flash('Section added.', 'success')
    return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))


@team_processes_bp.route('/team/<int:team_id>/process/<int:process_id>/sections/<int:section_id>/delete', methods=['POST'])
@login_required
@require_page_permission('team_processes', 'edit')
def delete_section(team_id: int, process_id: int, section_id: int):
    team_obj = Team.query.get_or_404(team_id)
    process = TeamProcess.query.filter_by(id=process_id, team_id=team_obj.id).first_or_404()
    section = TeamProcessSection.query.filter_by(id=section_id, process_id=process.id).first_or_404()

    if not _can_edit_section(current_user, process, section):
        flash('Only the creator can delete this section.', 'error')
        return redirect(url_for('team_processes.view_process', team_id=team_id, process_id=process_id))

    if section.created_by_user_id is None:
        section.created_by_user_id = current_user.id
        db.session.commit()

    db.session.delete(section)
    db.session.commit()

    flash('Section deleted.', 'success')
    return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))


@team_processes_bp.route('/team/<int:team_id>/process/<int:process_id>/sections/<int:section_id>/edit', methods=['GET', 'POST'])
@login_required
@require_page_permission('team_processes', 'edit')
def edit_section(team_id: int, process_id: int, section_id: int):
    team_obj = Team.query.get_or_404(team_id)
    process = TeamProcess.query.filter_by(id=process_id, team_id=team_obj.id).first_or_404()
    section = TeamProcessSection.query.filter_by(id=section_id, process_id=process.id).first_or_404()

    if not _can_edit_section(current_user, process, section):
        flash('Only the creator can edit this section.', 'error')
        return redirect(url_for('team_processes.view_process', team_id=team_id, process_id=process_id))

    if section.created_by_user_id is None:
        section.created_by_user_id = current_user.id
        db.session.commit()

    if request.method == 'POST':
        section_type = (request.form.get('section_type') or section.section_type or 'paragraph').strip()
        text_align = (request.form.get('text_align') or section.text_align or 'left').strip().lower()
        title = (request.form.get('title') or '').strip() or None
        title_html = (request.form.get('title_html') or '').strip() or None
        raw_content_html = (request.form.get('content_html') or '').strip() or None
        raw_content = (request.form.get('content') or '').strip() or None

        if raw_content_html is not None:
            content = _sanitize_html(raw_content_html)
        else:
            content = _sanitize_html(raw_content)

        title_html = _sanitize_title_html(title_html)

        if text_align not in ('left', 'center', 'right'):
            text_align = 'left'

        section.section_type = section_type
        section.text_align = text_align
        section.title = title
        section.title_html = title_html
        section.content = content
        db.session.commit()

        flash('Section updated.', 'success')
        return redirect(url_for('team_processes.view_process', team_id=team_obj.id, process_id=process.id))

    return render_template('team_processes/section_form.html', team=team_obj, process=process, section=section)
