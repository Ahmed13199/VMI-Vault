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
    teams = []
    if current_user.is_admin():
        teams = MetricsService.get_all_teams()
    elif current_user.team:
        teams = [current_user.team]
    
    # Build dashboard data
    dashboard_data = []
    
    if selected_period and teams:
        for team in teams:
            team_data = {
                'team': team,
                'base_metrics': [],
                'derived_metrics': []
            }
            
            # Get base metric values
            base_values = MetricsService.get_metric_values(team.id, selected_period.id)
            base_metrics = MetricsService.get_base_metrics_for_team(team.id)
            
            for metric in base_metrics:
                value = base_values.get(metric.key)
                team_data['base_metrics'].append({
                    'metric': metric,
                    'value': value,
                    'formatted': FormulaService.format_value(value, metric.unit) if value is not None else 'N/A'
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
                          dashboard_data=dashboard_data)
