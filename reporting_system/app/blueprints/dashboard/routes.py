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

    hide_without_targets = request.args.get('hide_without_targets') == '1'
    
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

    def has_target(config):
        if not config:
            return False
        if config.get('target_type') == 'range':
            return config.get('target_lower') is not None and config.get('target_upper') is not None
        return config.get('target') is not None

    def target_threshold_for_progress(config, trend_direction):
        if not has_target(config):
            return None
        if config.get('target_type') == 'range':
            if trend_direction == 'higher_is_better':
                return config.get('target_lower')
            return config.get('target_upper')
        return config.get('target')

    def classify_limit_status(value, config, trend_direction):
        if value is None or not has_target(config):
            return 'no-limit'
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 'no-limit'

        if config.get('target_type') == 'range':
            lower = float(config.get('target_lower'))
            upper = float(config.get('target_upper'))
            if lower <= v <= upper:
                return 'within-limit'
            if trend_direction == 'higher_is_better':
                return 'within-limit' if v > upper else 'limit-exceeded'
            if trend_direction == 'lower_is_better':
                return 'within-limit' if v < lower else 'limit-exceeded'
            return 'limit-exceeded'

        t = float(config.get('target'))
        if trend_direction == 'higher_is_better':
            return 'within-limit' if v >= t else 'limit-exceeded'
        if trend_direction == 'lower_is_better':
            return 'within-limit' if v <= t else 'limit-exceeded'
        return 'within-limit' if v <= t else 'limit-exceeded'

    def _mix_hex(start_hex, end_hex, amount):
        amount = max(0.0, min(float(amount), 1.0))
        start = start_hex.lstrip('#')
        end = end_hex.lstrip('#')
        rgb = []
        for i in range(0, 6, 2):
            s = int(start[i:i + 2], 16)
            e = int(end[i:i + 2], 16)
            rgb.append(round(s + ((e - s) * amount)))
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    def _hex_to_rgb(hex_color):
        value = hex_color.lstrip('#')
        return tuple(int(value[i:i + 2], 16) for i in range(0, 6, 2))

    def range_card_presentation(value, config, trend_direction, fallback_status):
        fallback_color = 'red' if fallback_status in ('limit-exceeded', 'bad') else 'green'
        if value is None or not has_target(config) or config.get('target_type') != 'range':
            return fallback_color, ''
        if trend_direction not in ('higher_is_better', 'lower_is_better'):
            return fallback_color, ''

        try:
            v = float(value)
            lower = float(config.get('target_lower'))
            upper = float(config.get('target_upper'))
        except (TypeError, ValueError):
            return fallback_color, ''

        if abs(upper - lower) < 1e-12:
            return fallback_color, ''

        if trend_direction == 'lower_is_better':
            if v < lower:
                return 'green', ''
            if v > upper:
                return 'red', ''
            severity = (v - lower) / (upper - lower)
            accent = _mix_hex('#eab308', '#ef4444', severity)
        else:
            if v > upper:
                return 'green', ''
            if v < lower:
                return 'red', ''
            severity = 1.0 - ((v - lower) / (upper - lower))
            accent = _mix_hex('#eab308', '#ef4444', severity)

        bg_start = _mix_hex('#050a10', accent, 0.16)
        bg_mid = _mix_hex('#050a10', accent, 0.24)
        bg_end = _mix_hex('#050a10', accent, 0.32)
        r, g, b = _hex_to_rgb(accent)
        card_style = (
            f'--range-card-bg: linear-gradient(145deg, {bg_start} 0%, {bg_mid} 60%, {bg_end} 100%); '
            f'--range-accent: {accent}; '
            f'--range-accent-soft: rgba({r}, {g}, {b}, 0.12); '
            f'--range-border: rgba({r}, {g}, {b}, 0.30);'
        )
        return 'range-scale', card_style

    def compute_achievement_stars(value, config, trend_direction):
        threshold = target_threshold_for_progress(config, trend_direction)
        if value is None or threshold is None:
            return 0
        try:
            v = float(value)
            t = float(threshold)
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

    def compute_limit_progress_pct(value, config, trend_direction):
        threshold = target_threshold_for_progress(config, trend_direction)
        if value is None or threshold is None:
            return 0
        try:
            v = abs(float(value))
            t = abs(float(threshold))
        except (TypeError, ValueError):
            return 0
        if t <= 1e-12:
            return 100 if v > 0 else 0
        return max(0, min((v / t) * 100.0, 100))

    def compute_limit_ratio_pct(value, config, trend_direction):
        threshold = target_threshold_for_progress(config, trend_direction)
        if value is None or threshold is None:
            return None
        try:
            v = abs(float(value))
            t = abs(float(threshold))
        except (TypeError, ValueError):
            return None
        if t <= 1e-12:
            return None
        return (v / t) * 100.0

    def compute_ring_offset(progress_pct):
        circumference = 427.26
        return circumference - ((progress_pct or 0) / 100.0) * circumference

    def split_metric_name(display_name):
        parts = (display_name or '').strip().split(' ', 1)
        subject = parts[0] if parts and parts[0] else 'Metric'
        title = parts[1] if len(parts) > 1 else display_name
        return subject, title

    def format_target_label(config, unit):
        if not has_target(config):
            return None
        if config.get('target_type') == 'range':
            lower = FormulaService.format_value(config.get('target_lower'), unit)
            upper = FormulaService.format_value(config.get('target_upper'), unit)
            return f'{lower} - {upper}'
        return FormulaService.format_value(config.get('target'), unit)

    def format_limit_difference(value, config, trend_direction):
        if value is None or not has_target(config):
            return None
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None

        if config.get('target_type') == 'range':
            lower = float(config.get('target_lower'))
            upper = float(config.get('target_upper'))
            if lower <= v <= upper:
                return None
            if trend_direction == 'higher_is_better' and v > upper:
                return None
            if trend_direction == 'lower_is_better' and v < lower:
                return None
            diff = v - lower if v < lower else v - upper
        else:
            diff = v - float(config.get('target'))
            if abs(diff) < 1e-12:
                return None

        formatted = FormulaService.format_value(abs(diff), 'number')
        if trend_direction == 'higher_is_better':
            return f'+{formatted} above' if diff > 0 else f'-{formatted} under'
        return f'+{formatted} over' if diff > 0 else f'-{formatted} under'

    def format_previous_delta(value, previous_value, trend_direction):
        if value is None or previous_value is None:
            return 'No previous data'
        try:
            diff = float(value) - float(previous_value)
        except (TypeError, ValueError):
            return 'No previous data'
        if abs(diff) < 1e-12:
            return 'No change from last week'
        direction = 'up' if diff > 0 else 'down'
        formatted = FormulaService.format_value(abs(diff), 'number')
        sign = '+' if diff > 0 else '-'
        return f'{sign}{formatted} from last week'

    def status_label(limit_status, trend_direction):
        if limit_status == 'no-limit':
            return 'No limit'
        if limit_status == 'within-limit':
            return 'Within target' if trend_direction != 'higher_is_better' else 'Target met'
        if trend_direction == 'higher_is_better':
            return 'Below target'
        return 'Over limit'
    
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
            previous_period = None
            prev_base_values = {}
            for period in periods:
                if selected_period and period.start_date < selected_period.start_date:
                    previous_period = period
                    break
            if previous_period:
                prev_base_values = MetricsService.get_metric_values(team.id, previous_period.id)
            base_metrics = MetricsService.get_base_metrics_for_team(team.id)
            
            for metric in base_metrics:
                entry = base_values_with_targets.get(metric.key) or {}
                value = entry.get('value')
                target = entry.get('target')
                target_type = entry.get('target_type') or 'single'
                target_lower = entry.get('target_lower')
                target_upper = entry.get('target_upper')
                target_config = {
                    'target_type': target_type if target_type in ('single', 'range') else 'single',
                    'target': target,
                    'target_lower': target_lower,
                    'target_upper': target_upper,
                }
                has_target_value = has_target(target_config)
                if hide_without_targets and not has_target_value:
                    continue

                trend_direction = getattr(metric, 'trend_direction', 'neutral')
                limit_status = classify_limit_status(
                    value,
                    target_config,
                    trend_direction
                )
                subject_label, metric_title = split_metric_name(metric.display_name)
                limit_progress_pct = compute_limit_progress_pct(value, target_config, trend_direction)
                limit_ratio_pct = compute_limit_ratio_pct(value, target_config, trend_direction)
                prev_value = prev_base_values.get(metric.key)
                ratio_label = f'{limit_ratio_pct:.0f}% of limit' if limit_ratio_pct is not None else 'No limit'
                if target_type == 'range' and has_target_value:
                    ratio_label = 'In target range' if limit_status == 'within-limit' else 'Outside range'
                card_color, card_style = range_card_presentation(
                    value,
                    target_config,
                    trend_direction,
                    limit_status,
                )
                if not has_target_value:
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
                    'target_type': target_type,
                    'target_lower': target_lower,
                    'target_upper': target_upper,
                    'has_target': has_target_value,
                    'limit_status': limit_status,
                    'card_color': card_color,
                    'card_style': card_style,
                    'status_label': status_label(limit_status, trend_direction),
                    'subject_label': subject_label,
                    'subject_initial': subject_label[:1].upper(),
                    'metric_title': metric_title,
                    'achievement_stars': compute_achievement_stars(
                        value,
                        target_config,
                        trend_direction
                    ),
                    'limit_progress_pct': limit_progress_pct,
                    'limit_ratio_pct': limit_ratio_pct,
                    'ring_offset': compute_ring_offset(limit_progress_pct),
                    'ratio_label': ratio_label,
                    'limit_delta_label': format_limit_difference(value, target_config, trend_direction),
                    'previous_delta_label': format_previous_delta(value, prev_value, trend_direction),
                    'period_label': selected_period.label if selected_period else '',
                    'formatted': FormulaService.format_value(value, metric.unit) if value is not None else 'N/A',
                    'target_formatted': format_target_label(target_config, metric.unit),
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
                          hide_without_targets=hide_without_targets,
                          dashboard_data=dashboard_data)
