"""
Settings routes for metric definition management.
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from . import settings_bp
from ...permissions import require_page_permission
from ...services.metrics_service import MetricsService
from ...services.access_service import AccessService
from ...services.auth_service import AuthService
from ...services.formula_service import FormulaService
from ...extensions import db
from ...models.metric import MetricDefinition
from ...models.graph_settings import GraphLayerSettings
from ...models.team import Team
from ...models.user import User


def _role_for_team_and_rank(team, rank):
    if rank == 'admin':
        return 'admin'
    if team and team.type:
        return team.type
    if team and team.name:
        return team.name.strip().lower().replace(' ', '_')
    return 'experience'


def _can_manage_target_user(actor, target):
    if actor is None or target is None:
        return False
    if not actor.can_edit_page('user_management'):
        return False
    if target.effective_rank() == 'admin':
        return False
    return True


@settings_bp.route('/')
@login_required
@require_page_permission('settings')
def index():
    """
    List all metric definitions.
    """
    metrics = MetricsService.get_all_metrics_for_user(current_user, include_inactive=True)
    teams = MetricsService.get_all_teams()
    categories = MetricsService.get_all_categories_with_sub_categories_for_user(current_user)
    sub_categories = MetricsService.get_all_sub_categories_with_categories_for_user(current_user)
    active_tab = request.args.get('tab', 'metrics')
    permission_groups = AccessService.get_permission_matrix() if current_user.can_access_page('permissions') else {}
    team_user_counts = {}
    team_filter = request.args.get('team_filter', type=int)
    rank_filter = (request.args.get('rank_filter') or '').strip()
    user_search = (request.args.get('user_search') or '').strip()
    user_page = max(request.args.get('user_page', default=1, type=int), 1)
    users_per_page = 10
    users = []
    users_total = 0
    users_pages = 0

    if current_user.can_access_page('user_management'):
        users_query = User.query.options(joinedload(User.team))

        if user_search:
            like_value = f'%{user_search}%'
            users_query = users_query.filter(
                or_(
                    User.first_name.ilike(like_value),
                    User.last_name.ilike(like_value),
                    User.username.ilike(like_value),
                    func.concat(func.coalesce(User.first_name, ''), ' ', func.coalesce(User.last_name, '')).ilike(like_value),
                )
            )

        if rank_filter:
            users_query = users_query.filter(User.rank == rank_filter)

        if team_filter:
            users_query = users_query.filter(User.team_id == team_filter)

        users_total = users_query.count()
        users_pages = max((users_total + users_per_page - 1) // users_per_page, 1) if users_total else 1
        if user_page > users_pages:
            user_page = users_pages

        users = (
            users_query.order_by(User.first_name.asc(), User.last_name.asc(), User.username.asc())
            .offset((user_page - 1) * users_per_page)
            .limit(users_per_page)
            .all()
        )

    if current_user.can_access_page('team_management'):
        team_user_counts = dict(
            db.session.query(User.team_id, func.count(User.id))
            .filter(User.team_id.isnot(None))
            .group_by(User.team_id)
            .all()
        )
    
    return render_template('settings/index.html', 
                          metrics=metrics,
                          teams=teams,
                          categories=categories,
                          sub_categories=sub_categories,
                          active_tab=active_tab,
                          permission_groups=permission_groups,
                          users=users,
                          rank_options=User.RANKS,
                          team_user_counts=team_user_counts,
                          user_search=user_search,
                          team_filter=team_filter,
                          rank_filter=rank_filter,
                          user_page=user_page,
                          users_pages=users_pages,
                          users_total=users_total)


@settings_bp.route('/categories', methods=['GET'])
@login_required
@require_page_permission('settings')
def categories_index():
    categories = MetricsService.get_all_categories_with_sub_categories_for_user(current_user)
    sub_categories = MetricsService.get_all_sub_categories_with_categories_for_user(current_user)
    return render_template('settings/categories.html', categories=categories, sub_categories=sub_categories)


@settings_bp.route('/categories/<int:category_id>/rename', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def rename_category(category_id):
    new_name = request.form.get('name', '').strip()
    allowed_ids = {c.id for c in MetricsService.get_all_categories_with_sub_categories_for_user(current_user)}
    if category_id not in allowed_ids:
        flash('Not authorized to edit this category.', 'error')
        return redirect(url_for('settings.categories_index'))
    try:
        category = MetricsService.rename_category(category_id, new_name)
        flash(f'Category renamed to "{category.name}".', 'success')
    except Exception as e:
        flash(f'Error renaming category: {str(e)}', 'error')
    return redirect(url_for('settings.categories_index'))


@settings_bp.route('/sub-categories/<int:sub_category_id>/rename', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def rename_sub_category(sub_category_id):
    new_name = request.form.get('name', '').strip()
    allowed_ids = {sc.id for sc in MetricsService.get_all_sub_categories_with_categories_for_user(current_user)}
    if sub_category_id not in allowed_ids:
        flash('Not authorized to edit this sub-category.', 'error')
        return redirect(url_for('settings.categories_index'))
    try:
        sub_category = MetricsService.rename_sub_category(sub_category_id, new_name)
        flash(f'Sub-category renamed to "{sub_category.name}".', 'success')
    except Exception as e:
        flash(f'Error renaming sub-category: {str(e)}', 'error')
    return redirect(url_for('settings.categories_index'))


@settings_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def delete_category(category_id):
    allowed_ids = {c.id for c in MetricsService.get_all_categories_with_sub_categories_for_user(current_user)}
    if category_id not in allowed_ids:
        flash('Not authorized to delete this category.', 'error')
        return redirect(url_for('settings.categories_index'))
    try:
        success, message = MetricsService.delete_category(category_id)
        flash(message, 'success' if success else 'error')
    except Exception as e:
        flash(f'Error deleting category: {str(e)}', 'error')
    return redirect(url_for('settings.categories_index'))


@settings_bp.route('/sub-categories/<int:sub_category_id>/delete', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def delete_sub_category(sub_category_id):
    allowed_ids = {sc.id for sc in MetricsService.get_all_sub_categories_with_categories_for_user(current_user)}
    if sub_category_id not in allowed_ids:
        flash('Not authorized to delete this sub-category.', 'error')
        return redirect(url_for('settings.categories_index'))
    try:
        success, message = MetricsService.delete_sub_category(sub_category_id)
        flash(message, 'success' if success else 'error')
    except Exception as e:
        flash(f'Error deleting sub-category: {str(e)}', 'error')
    return redirect(url_for('settings.categories_index'))


@settings_bp.route('/metrics/categories', methods=['GET'])
@login_required
@require_page_permission('settings')
def metric_categories():
    return jsonify({'categories': MetricsService.get_all_category_names_for_user(current_user)})


@settings_bp.route('/metrics/sub-categories', methods=['GET'])
@login_required
@require_page_permission('settings')
def metric_sub_categories():
    category = request.args.get('category', '').strip() or None
    return jsonify({'sub_categories': MetricsService.get_sub_category_names_for_category_for_user(current_user, category)})


@settings_bp.route('/metrics/categories', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def create_metric_category():
    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip() or None
    try:
        category = MetricsService.create_category(name)
        allowed_team_ids = MetricsService._allowed_team_ids_for_user(current_user)
        if allowed_team_ids not in (None, []):
            MetricsService._link_category_to_teams(category, allowed_team_ids)
            db.session.commit()
        return jsonify({'ok': True, 'category': category.name, 'categories': MetricsService.get_all_category_names_for_user(current_user)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@settings_bp.route('/metrics/sub-categories', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def create_metric_sub_category():
    payload = request.get_json(silent=True) or {}
    category_name = (payload.get('category') or '').strip() or None
    name = (payload.get('name') or '').strip() or None
    try:
        allowed_categories = set(MetricsService.get_all_category_names_for_user(current_user))
        if category_name and category_name not in allowed_categories:
            return jsonify({'ok': False, 'error': 'Not authorized to add sub-categories to this category.'}), 403
        sub_category = MetricsService.create_sub_category(category_name, name)
        return jsonify({
            'ok': True,
            'sub_category': sub_category.name,
            'sub_categories': MetricsService.get_sub_category_names_for_category_for_user(current_user, category_name)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@settings_bp.route('/metrics/new', methods=['GET', 'POST'])
@login_required
@require_page_permission('settings', 'edit')
def create_metric():
    """
    Create a new metric definition.
    """
    teams = MetricsService.get_all_teams_for_user(current_user)
    existing_metrics = MetricsService.get_all_metrics_for_user(current_user)
    
    if request.method == 'POST':
        # Extract form data
        key = request.form.get('key', '').strip().lower().replace(' ', '_')
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip() or None
        category = request.form.get('category', '').strip() or None
        sub_category = request.form.get('sub_category', '').strip() or None
        trend_direction = request.form.get('trend_direction', 'neutral')
        unit = request.form.get('unit', 'number')
        allowed_team_ids = {t.id for t in teams}
        team_ids = [int(t) for t in request.form.getlist('team_ids') if str(t).strip().isdigit() and int(t) in allowed_team_ids]
        scope = 'team' if team_ids else 'global'
        is_derived = request.form.get('is_derived') == 'on'
        formula = request.form.get('formula', '').strip() if is_derived else None
        layer = request.form.get('layer', type=int, default=1)
        
        # Validation
        errors = []
        
        if not key:
            errors.append('Metric key is required.')
        elif not key.replace('_', '').isalnum():
            errors.append('Metric key must contain only letters, numbers, and underscores.')
        elif MetricsService.get_metric_by_key(key):
            errors.append(f'Metric key "{key}" already exists.')
        
        if not display_name:
            errors.append('Display name is required.')

        if trend_direction not in MetricDefinition.TREND_DIRECTIONS:
            errors.append('Trend direction is invalid.')
        
        if is_derived:
            if not formula:
                errors.append('Formula is required for derived metrics.')
            else:
                # Validate formula
                available_keys = {m.key for m in existing_metrics}
                formula_errors = FormulaService.validate_formula(formula, available_keys)
                errors.extend(formula_errors)
            
            if layer < 2:
                layer = 2  # Derived metrics must be layer 2+
        else:
            layer = 1  # Base metrics are always layer 1
        
        if scope == 'team' and not team_ids:
            errors.append('At least one team must be selected for team-specific metrics.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('settings/metric_form.html',
                                  teams=teams,
                                  existing_metrics=existing_metrics,
                                  form_data=request.form,
                                  is_edit=False)
        
        # Create metric
        try:
            metric = MetricsService.create_metric(
                key=key,
                display_name=display_name,
                description=description,
                category=category,
                sub_category=sub_category,
                trend_direction=trend_direction,
                unit=unit,
                scope=scope,
                team_ids=team_ids,
                is_derived=is_derived,
                formula=formula,
                layer=layer
            )
            flash(f'Metric "{display_name}" created successfully.', 'success')
            return redirect(url_for('settings.index'))
        except Exception as e:
            flash(f'Error creating metric: {str(e)}', 'error')
    
    return render_template('settings/metric_form.html',
                          teams=teams,
                          existing_metrics=existing_metrics,
                          form_data={},
                          is_edit=False)


@settings_bp.route('/metrics/<int:metric_id>/edit', methods=['GET', 'POST'])
@login_required
@require_page_permission('settings', 'edit')
def edit_metric(metric_id):
    """
    Edit an existing metric definition.
    """
    metric = MetricsService.get_metric_by_id(metric_id)
    if not metric:
        flash('Metric not found.', 'error')
        return redirect(url_for('settings.index'))

    allowed_metric_ids = {m.id for m in MetricsService.get_all_metrics_for_user(current_user, include_inactive=True)}
    if metric_id not in allowed_metric_ids:
        flash('Not authorized to edit this metric.', 'error')
        return redirect(url_for('settings.index'))
    
    teams = MetricsService.get_all_teams_for_user(current_user)
    existing_metrics = [m for m in MetricsService.get_all_metrics_for_user(current_user) if m.id != metric_id]
    
    if request.method == 'POST':
        # Extract form data
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip() or None
        category = request.form.get('category', '').strip() or None
        sub_category = request.form.get('sub_category', '').strip() or None
        trend_direction = request.form.get('trend_direction', 'neutral')
        unit = request.form.get('unit', 'number')
        allowed_team_ids = {t.id for t in teams}
        team_ids = [int(t) for t in request.form.getlist('team_ids') if str(t).strip().isdigit() and int(t) in allowed_team_ids]
        scope = 'team' if team_ids else 'global'
        is_derived = request.form.get('is_derived') == 'on'
        formula = request.form.get('formula', '').strip() if is_derived else None
        layer = request.form.get('layer', type=int, default=1)
        active = request.form.get('active') == 'on'
        
        # Validation
        errors = []
        
        if not display_name:
            errors.append('Display name is required.')

        if trend_direction not in MetricDefinition.TREND_DIRECTIONS:
            errors.append('Trend direction is invalid.')
        
        if is_derived:
            if not formula:
                errors.append('Formula is required for derived metrics.')
            else:
                available_keys = {m.key for m in existing_metrics}
                formula_errors = FormulaService.validate_formula(formula, available_keys)
                errors.extend(formula_errors)
            
            if layer < 2:
                layer = 2
        else:
            layer = 1
        
        if scope == 'team' and not team_ids:
            errors.append('At least one team must be selected for team-specific metrics.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('settings/metric_form.html',
                                  teams=teams,
                                  existing_metrics=existing_metrics,
                                  metric=metric,
                                  form_data=request.form,
                                  is_edit=True)
        
        # Update metric
        try:
            MetricsService.update_metric(
                metric_id,
                display_name=display_name,
                description=description,
                category=category,
                sub_category=sub_category,
                trend_direction=trend_direction,
                unit=unit,
                scope=scope,
                team_id=None,
                scoped_teams=[t for t in teams if t.id in team_ids],
                is_derived=is_derived,
                formula=formula,
                layer=layer,
                active=active
            )
            flash(f'Metric "{display_name}" updated successfully.', 'success')
            return redirect(url_for('settings.index'))
        except Exception as e:
            flash(f'Error updating metric: {str(e)}', 'error')
    
    return render_template('settings/metric_form.html',
                          teams=teams,
                          existing_metrics=existing_metrics,
                          metric=metric,
                          form_data={},
                          is_edit=True)


@settings_bp.route('/metrics/<int:metric_id>/delete', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def delete_metric(metric_id):
    """
    Deactivate a metric definition.
    """
    metric = MetricsService.get_metric_by_id(metric_id)
    if not metric:
        flash('Metric not found.', 'error')
        return redirect(url_for('settings.index'))

    allowed_metric_ids = {m.id for m in MetricsService.get_all_metrics_for_user(current_user, include_inactive=True)}
    if metric_id not in allowed_metric_ids:
        flash('Not authorized to update this metric.', 'error')
        return redirect(url_for('settings.index'))
    
    try:
        MetricsService.delete_metric(metric_id)
        flash(f'Metric "{metric.display_name}" has been deactivated.', 'success')
    except Exception as e:
        flash(f'Error deactivating metric: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))


@settings_bp.route('/metrics/<int:metric_id>/activate', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def activate_metric(metric_id):
    metric = MetricsService.get_metric_by_id(metric_id)
    if not metric:
        flash('Metric not found.', 'error')
        return redirect(url_for('settings.index'))

    allowed_metric_ids = {m.id for m in MetricsService.get_all_metrics_for_user(current_user, include_inactive=True)}
    if metric_id not in allowed_metric_ids:
        flash('Not authorized to update this metric.', 'error')
        return redirect(url_for('settings.index'))

    try:
        MetricsService.set_metric_active(metric_id, True)
        flash(f'Metric "{metric.display_name}" activated.', 'success')
    except Exception as e:
        flash(f'Error activating metric: {str(e)}', 'error')

    return redirect(url_for('settings.index'))


@settings_bp.route('/metrics/<int:metric_id>/deactivate', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def deactivate_metric(metric_id):
    metric = MetricsService.get_metric_by_id(metric_id)
    if not metric:
        flash('Metric not found.', 'error')
        return redirect(url_for('settings.index'))

    allowed_metric_ids = {m.id for m in MetricsService.get_all_metrics_for_user(current_user, include_inactive=True)}
    if metric_id not in allowed_metric_ids:
        flash('Not authorized to update this metric.', 'error')
        return redirect(url_for('settings.index'))

    try:
        MetricsService.set_metric_active(metric_id, False)
        flash(f'Metric "{metric.display_name}" deactivated.', 'success')
    except Exception as e:
        flash(f'Error deactivating metric: {str(e)}', 'error')

    return redirect(url_for('settings.index'))


@settings_bp.route('/metrics/<int:metric_id>/delete-permanent', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def delete_metric_permanently(metric_id):
    metric = MetricsService.get_metric_by_id(metric_id)
    if not metric:
        flash('Metric not found.', 'error')
        return redirect(url_for('settings.index'))

    allowed_metric_ids = {m.id for m in MetricsService.get_all_metrics_for_user(current_user, include_inactive=True)}
    if metric_id not in allowed_metric_ids:
        flash('Not authorized to delete this metric.', 'error')
        return redirect(url_for('settings.index'))

    try:
        success, message = MetricsService.delete_metric_permanently(metric_id)
        flash(message, 'success' if success else 'error')
    except Exception as e:
        flash(f'Error permanently deleting metric: {str(e)}', 'error')

    return redirect(url_for('settings.index'))


@settings_bp.route('/api/validate-formula', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def validate_formula():
    """
    API endpoint to validate a formula string.
    """
    data = request.get_json()
    formula = data.get('formula', '')
    
    existing_metrics = MetricsService.get_all_metrics_for_user(current_user)
    available_keys = {m.key for m in existing_metrics}
    
    errors = FormulaService.validate_formula(formula, available_keys)
    
    return jsonify({
        'valid': len(errors) == 0,
        'errors': errors
    })


@settings_bp.route('/graph')
@login_required
@require_page_permission('settings')
def metrics_graph():
    """
    Visual graph view of metrics and their dependencies.
    """
    metrics = MetricsService.get_all_metrics_for_user(current_user, include_inactive=False)
    
    # Ensure default graph settings exist for all layers
    max_layer = max((m.layer for m in metrics), default=1)
    GraphLayerSettings.ensure_defaults_exist(max_layer)
    
    # Get graph layer settings
    layer_settings = GraphLayerSettings.get_all_settings()
    
    # Build nodes and edges for the graph
    nodes = []
    edges = []
    
    for metric in metrics:
        nodes.append({
            'id': metric.key,
            'label': metric.display_name,
            'layer': metric.layer,
            'is_derived': metric.is_derived,
            'formula': metric.formula or '',
            'unit': metric.unit
        })
        
        # Extract dependencies from formula
        if metric.is_derived and metric.formula:
            dependencies = FormulaService.extract_metric_keys(metric.formula)
            for dep_key in dependencies:
                edges.append({
                    'from': dep_key,
                    'to': metric.key
                })
    
    return render_template('settings/graph.html',
                          nodes=nodes,
                          edges=edges,
                          layer_settings=layer_settings,
                          shapes=GraphLayerSettings.SHAPES)


@settings_bp.route('/api/graph-settings', methods=['GET'])
@login_required
@require_page_permission('settings')
def get_graph_settings():
    """
    API endpoint to get all graph layer settings.
    """
    settings = GraphLayerSettings.get_all_settings()
    return jsonify({
        'settings': settings,
        'shapes': GraphLayerSettings.SHAPES
    })


@settings_bp.route('/api/graph-settings/<int:layer>', methods=['POST'])
@login_required
@require_page_permission('settings', 'edit')
def update_graph_settings(layer):
    """
    API endpoint to update graph settings for a specific layer.
    """
    data = request.get_json()
    
    color = data.get('color')
    shape = data.get('shape')
    size = data.get('size')
    
    if size is not None:
        try:
            size = int(size)
        except (ValueError, TypeError):
            size = None
    
    setting = GraphLayerSettings.update_setting(layer, color=color, shape=shape, size=size)
    
    return jsonify({
        'success': True,
        'setting': setting.to_dict()
    })


@settings_bp.route('/access-control', methods=['GET', 'POST'])
@login_required
@require_page_permission('permissions')
def access_control():
    if request.method == 'POST':
        AccessService.save_from_form(request.form)
        flash('Access permissions updated successfully.', 'success')
    return redirect(url_for('settings.index', tab='permissions'))


@settings_bp.route('/users/new', methods=['POST'])
@login_required
@require_page_permission('user_management', 'edit')
def create_user():
    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    rank = (request.form.get('rank') or 'agent').strip()
    team_id = request.form.get('team_id', type=int)

    if not first_name or not last_name or not username or not password:
        flash('First name, last name, username, and password are required.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    if rank not in User.RANKS:
        flash('Invalid rank selected.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    if User.query.filter_by(username=username).first():
        flash(f'Username "{username}" already exists.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    team = MetricsService.get_team_by_id(team_id) if team_id else None
    role = _role_for_team_and_rank(team, rank)

    AuthService.create_user(
        username=username,
        password=password,
        role=role,
        team_id=team.id if team else None,
        rank=rank,
        first_name=first_name,
        last_name=last_name,
    )
    flash(f'User "{username}" created successfully.', 'success')
    return redirect(url_for('settings.index', tab='users'))


@settings_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@require_page_permission('user_management', 'edit')
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    if not _can_manage_target_user(current_user, user):
        flash('Admin accounts cannot be edited by another admin.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    rank = (request.form.get('rank') or user.effective_rank()).strip()
    team_id = request.form.get('team_id', type=int)

    if not first_name or not last_name or not username:
        flash('First name, last name, and username are required.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    if rank not in User.RANKS:
        flash('Invalid rank selected.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    existing = User.query.filter(User.username == username, User.id != user.id).first()
    if existing:
        flash(f'Username "{username}" already exists.', 'error')
        return redirect(url_for('settings.index', tab='users'))

    team = MetricsService.get_team_by_id(team_id) if team_id else None

    user.first_name = first_name
    user.last_name = last_name
    user.username = username
    user.rank = rank
    user.team_id = team.id if team else None
    user.role = _role_for_team_and_rank(team, rank)
    if password.strip():
        user.set_password(password)

    db.session.commit()
    flash(f'User "{user.username}" updated successfully.', 'success')
    return redirect(url_for('settings.index', tab='users'))


@settings_bp.route('/teams/new', methods=['POST'])
@login_required
@require_page_permission('team_management', 'edit')
def create_team():
    name = (request.form.get('name') or '').strip()
    type_value = (request.form.get('type') or '').strip() or None

    if not name:
        flash('Team name is required.', 'error')
        return redirect(url_for('settings.index', tab='teams'))

    existing = Team.query.filter_by(name=name).first()
    if existing:
        flash(f'Team "{name}" already exists.', 'error')
        return redirect(url_for('settings.index', tab='teams'))

    team = Team(name=name, type=type_value)
    db.session.add(team)
    db.session.commit()
    flash(f'Team "{name}" created successfully.', 'success')
    return redirect(url_for('settings.index', tab='teams'))


@settings_bp.route('/teams/<int:team_id>/edit', methods=['POST'])
@login_required
@require_page_permission('team_management', 'edit')
def update_team(team_id):
    team = Team.query.get_or_404(team_id)
    name = (request.form.get('name') or '').strip()
    type_value = (request.form.get('type') or '').strip() or None

    if not name:
        flash('Team name is required.', 'error')
        return redirect(url_for('settings.index', tab='teams'))

    existing = Team.query.filter(Team.name == name, Team.id != team.id).first()
    if existing:
        flash(f'Team "{name}" already exists.', 'error')
        return redirect(url_for('settings.index', tab='teams'))

    team.name = name
    team.type = type_value
    db.session.commit()
    flash(f'Team "{name}" updated successfully.', 'success')
    return redirect(url_for('settings.index', tab='teams'))


@settings_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
@require_page_permission('team_management', 'edit')
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)

    has_users = User.query.filter_by(team_id=team.id).first() is not None
    has_direct_metrics = MetricDefinition.query.filter_by(team_id=team.id).first() is not None
    has_scoped_metrics = len(team.scoped_metrics) > 0
    has_categories = len(team.metric_categories) > 0

    if has_users or has_direct_metrics or has_scoped_metrics or has_categories:
        flash('Team cannot be deleted while it is still assigned to users, metrics, or categories.', 'error')
        return redirect(url_for('settings.index', tab='teams'))

    db.session.delete(team)
    db.session.commit()
    flash(f'Team "{team.name}" deleted successfully.', 'success')
    return redirect(url_for('settings.index', tab='teams'))
