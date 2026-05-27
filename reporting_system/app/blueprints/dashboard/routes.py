"""
Dashboard routes.
"""
from flask import render_template, request
from flask_login import login_required, current_user
from . import dashboard_bp
from ...permissions import require_page_permission
from ...services.metrics_service import MetricsService
from ...services.formula_service import FormulaService


@dashboard_bp.route('/')
@login_required
@require_page_permission('dashboard')
def index():
    """
    Main dashboard page showing KPI overview.
    """
    # Get available periods
    periods = MetricsService.get_recent_periods(limit=12)
    
    # Get selected period (default to most recent)
    period_id = request.args.get('period_id', type=int)
    selected_period = None
    
    if period_id:
        selected_period = MetricsService.get_period_by_id(period_id)
    elif periods:
        selected_period = periods[0]
    
    # Determine which teams to show
    all_teams = []
    selected_team_ids = []
    teams = []
    if current_user.is_admin():
        all_teams = MetricsService.get_all_teams()
        requested_team_ids = request.args.getlist('team_id', type=int)
        available_team_ids = {team.id for team in all_teams}
        selected_team_ids = [
            team_id for team_id in requested_team_ids
            if team_id in available_team_ids
        ] or [team.id for team in all_teams]
        teams = [team for team in all_teams if team.id in selected_team_ids]
    elif current_user.team:
        teams = [current_user.team]
        selected_team_ids = [current_user.team.id]

    def classify_limit_status(value, target, trend_direction):
        if value is None or target is None:
            return 'no-limit'
        try:
            v = float(value)
            t = float(target)
        except (TypeError, ValueError):
            return 'no-limit'
        if trend_direction == 'higher_is_better':
            return 'within-limit' if v >= t else 'limit-exceeded'
        if trend_direction == 'lower_is_better':
            return 'within-limit' if v <= t else 'limit-exceeded'
        return 'within-limit' if v <= t else 'limit-exceeded'

    def compute_achievement_stars(value, target, trend_direction):
        if value is None or target is None:
            return 0
        try:
            v = float(value)
            t = float(target)
        except (TypeError, ValueError):
            return 0

        improvement = None
        if trend_direction == 'higher_is_better' and v > t:
            improvement = (v - t) / abs(t) if abs(t) > 1e-12 else v - t
        elif trend_direction == 'lower_is_better' and v < t:
            improvement = (t - v) / abs(t) if abs(t) > 1e-12 else t - v

        if improvement is None or improvement <= 0:
            return 0
        if improvement >= 0.5:
            return 3
        if improvement >= 0.2:
            return 2
        return 1

    def compute_limit_progress_pct(value, target):
        if value is None or target is None:
            return 0
        try:
            v = abs(float(value))
            t = abs(float(target))
        except (TypeError, ValueError):
            return 0
        if t <= 1e-12:
            return 100 if v > 0 else 0
        return max(0, min((v / t) * 100.0, 100))
    
    # Build dashboard data
    dashboard_data = []
    
    if selected_period and teams:
        for team in teams:
            team_data = {
                'team': team,
                'base_metrics': [],
                'derived_metrics': [],
                'within_limit_count': 0,
                'limit_exceeded_count': 0,
                'without_limit_count': 0,
                'metrics_with_limits_count': 0,
            }
            
            # Get base metric values
            base_values_with_targets = MetricsService.get_metric_values_with_targets(team.id, selected_period.id)
            base_values = {
                key: entry.get('value')
                for key, entry in base_values_with_targets.items()
            }
            base_metrics = MetricsService.get_base_metrics_for_team(team.id)
            
            for metric in base_metrics:
                entry = base_values_with_targets.get(metric.key) or {}
                value = entry.get('value')
                target = entry.get('target')
                limit_status = classify_limit_status(
                    value,
                    target,
                    getattr(metric, 'trend_direction', 'neutral')
                )
                if target is None:
                    team_data['without_limit_count'] += 1
                else:
                    team_data['metrics_with_limits_count'] += 1
                    if limit_status == 'within-limit':
                        team_data['within_limit_count'] += 1
                    elif limit_status == 'limit-exceeded':
                        team_data['limit_exceeded_count'] += 1
                team_data['base_metrics'].append({
                    'metric': metric,
                    'value': value,
                    'target': target,
                    'limit_status': limit_status,
                    'achievement_stars': compute_achievement_stars(
                        value,
                        target,
                        getattr(metric, 'trend_direction', 'neutral')
                    ),
                    'limit_progress_pct': compute_limit_progress_pct(value, target),
                    'formatted': FormulaService.format_value(value, metric.unit) if value is not None else 'N/A',
                    'target_formatted': FormulaService.format_value(target, metric.unit) if target is not None else None,
                })
            
            # Calculate derived metrics
            derived_metrics = MetricsService.get_derived_metrics_for_team(team.id)
            derived_values = FormulaService.compute_derived_metrics(base_values, derived_metrics)
            
            for metric in derived_metrics:
                value = derived_values.get(metric.key)
                team_data['derived_metrics'].append({
                    'metric': metric,
                    'value': value,
                    'formatted': FormulaService.format_value(value, metric.unit) if value is not None else 'N/A'
                })
            
            dashboard_data.append(team_data)
    
    return render_template('dashboard/index.html',
                          periods=periods,
                          selected_period=selected_period,
                          all_teams=all_teams,
                          selected_team_ids=selected_team_ids,
                          dashboard_data=dashboard_data)
