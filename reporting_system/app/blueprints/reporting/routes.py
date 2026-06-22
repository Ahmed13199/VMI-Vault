"""
Reporting routes for data entry and output display.
"""
import math
import random
from datetime import datetime, timedelta, date
from collections import OrderedDict
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import reporting_bp
from ...permissions import require_page_permission
from ...services.access_service import AccessService
from ...services.metrics_service import MetricsService
from ...services.formula_service import FormulaService
from ...extensions import db
from ...models.metric import ReportingPeriod
from ...models.app_setting import AppSetting


BLEND_REPORT_SETTING_KEY = 'blend_report_user_id'


def _weekly_period_window():
    """Return generated weekly periods from week 40 through the next generated week."""
    MetricsService.ensure_weekly_periods_for_current_year(start_week=40)
    iso_year, iso_week, _ = date.today().isocalendar()
    start_week = 40
    last_week = min(iso_week + 1, 53)

    # Around end-of-year, ISO week/year can roll over (e.g. Dec 29 might be ISO week 1
    # of the next ISO year). In that case, the window "week 40 -> next week" spans the
    # previous ISO year and the current ISO year.
    try:
        start_bound_year = iso_year - 1 if iso_week < start_week else iso_year
        start_bound = date.fromisocalendar(start_bound_year, start_week, 1)
    except ValueError:
        start_bound = date(iso_year, 1, 1)
    try:
        end_bound = date.fromisocalendar(iso_year, last_week, 7)
    except ValueError:
        end_bound = date(iso_year, 12, 31)

    return (ReportingPeriod.query
            .filter(ReportingPeriod.period_type == 'weekly')
            .filter(ReportingPeriod.start_date >= start_bound)
            .filter(ReportingPeriod.end_date <= end_bound)
            .order_by(ReportingPeriod.start_date.desc())
            .all())


def _parse_optional_float(raw_value):
    raw_value = (raw_value or '').strip()
    if not raw_value:
        return None
    return float(raw_value)


def _target_config_from_entry(entry):
    entry = entry or {}
    target_type = entry.get('target_type') or 'single'
    if target_type not in ('single', 'range'):
        target_type = 'single'
    return {
        'target_type': target_type,
        'target': entry.get('target'),
        'target_lower': entry.get('target_lower'),
        'target_upper': entry.get('target_upper'),
    }


def _target_config_has_values(config):
    if not config:
        return False
    if config.get('target_type') == 'range':
        return config.get('target_lower') is not None and config.get('target_upper') is not None
    return config.get('target') is not None


def _blend_report_value(previous_value):
    """Return a rounded-up value within +/-3% of the previous value."""
    value = float(previous_value)
    adjusted = value * random.uniform(0.97, 1.03)
    return max(0, math.ceil(adjusted))


@reporting_bp.route('/input', methods=['GET', 'POST'])
@login_required
@require_page_permission('reporting_input')
def input():
    """
    Data entry page for layer 1 metrics.
    """
    # Data entry is limited to the two completed weeks before the latest generated week.
    periods = _weekly_period_window()[1:3]
    teams = MetricsService.get_all_teams()

    def get_previous_period(period):
        if not period:
            return None
        return (ReportingPeriod.query
                .filter(ReportingPeriod.period_type == period.period_type)
                .filter(ReportingPeriod.start_date < period.start_date)
                .order_by(ReportingPeriod.start_date.desc())
                .first())
    
    # Determine user's team
    user_team = current_user.team
    if current_user.is_admin():
        # Admin can select any team
        selected_team_id = request.args.get('team_id', type=int)
        if selected_team_id:
            user_team = MetricsService.get_team_by_id(selected_team_id)
    
    # Get selected period
    period_id = request.args.get('period_id', type=int)
    selected_period = None
    if period_id:
        selected_period = MetricsService.get_period_by_id(period_id)
        if selected_period and selected_period.id not in {period.id for period in periods}:
            selected_period = None
    if not selected_period and periods:
        selected_period = periods[0]
    
    # Handle form submission
    if request.method == 'POST':
        if not AccessService.can_access_page(current_user, 'reporting_input', 'edit'):
            return AccessService.deny_access('edit')
        action = request.form.get('action')
        
        # Create new period
        if action == 'create_period':
            period_type = request.form.get('period_type', 'weekly')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                if end_date <= start_date:
                    flash('End date must be after start date.', 'error')
                else:
                    # Generate label
                    if period_type == 'weekly':
                        label = MetricsService.generate_weekly_label(start_date)
                    else:
                        label = MetricsService.generate_monthly_label(start_date)
                    
                    period = MetricsService.create_period(period_type, start_date, end_date, label)
                    flash(f'Reporting period "{label}" created.', 'success')
                    return redirect(url_for('reporting.input', 
                                          period_id=period.id,
                                          team_id=user_team.id if user_team else None))
            except ValueError:
                flash('Invalid date format.', 'error')
        
        # Save metric values
        elif action == 'save_values':
            period_id = request.form.get('period_id', type=int)
            team_id = request.form.get('team_id', type=int)
            
            if not period_id or not team_id:
                flash('Period and team are required.', 'error')
            else:
                selected_period = MetricsService.get_period_by_id(period_id)
                user_team = MetricsService.get_team_by_id(team_id)
                previous_period = get_previous_period(selected_period)
                previous_values_with_targets = (
                    MetricsService.get_metric_values_with_targets(team_id, previous_period.id)
                    if previous_period else {}
                )
                
                # Get base metrics for this team
                base_metrics = MetricsService.get_base_metrics_for_team(team_id)
                
                saved_count = 0
                for metric in base_metrics:
                    value_str = request.form.get(f'metric_{metric.id}', '').strip()
                    if value_str:
                        try:
                            value = float(value_str)
                            target_type = request.form.get(f'target_type_{metric.id}', 'single')
                            if target_type not in ('single', 'range'):
                                target_type = 'single'

                            target = _parse_optional_float(request.form.get(f'target_{metric.id}'))
                            target_lower = _parse_optional_float(request.form.get(f'target_lower_{metric.id}'))
                            target_upper = _parse_optional_float(request.form.get(f'target_upper_{metric.id}'))

                            target_config = {
                                'target_type': target_type,
                                'target': target if target_type == 'single' else None,
                                'target_lower': target_lower if target_type == 'range' else None,
                                'target_upper': target_upper if target_type == 'range' else None,
                            }

                            if target_type == 'range':
                                has_lower = target_lower is not None
                                has_upper = target_upper is not None
                                if has_lower != has_upper:
                                    flash(f'Range target for {metric.display_name} needs both lower and upper values.', 'error')
                                    continue
                                if has_lower and target_lower > target_upper:
                                    flash(f'Range target for {metric.display_name} must have lower target less than or equal to upper target.', 'error')
                                    continue

                            previous_config = _target_config_from_entry(previous_values_with_targets.get(metric.key))
                            if (
                                not _target_config_has_values(target_config)
                                and _target_config_has_values(previous_config)
                                and target_config.get('target_type') == previous_config.get('target_type')
                            ):
                                target_config = previous_config

                            MetricsService.save_metric_value_with_target(
                                metric.id,
                                team_id,
                                period_id,
                                value,
                                target_config.get('target'),
                                target_config.get('target_type', 'single'),
                                target_config.get('target_lower'),
                                target_config.get('target_upper'),
                            )
                            saved_count += 1
                        except ValueError:
                            flash(f'Invalid value for {metric.display_name}.', 'error')
                
                if saved_count > 0:
                    flash(f'Saved {saved_count} metric value(s).', 'success')
                
                return redirect(url_for('reporting.input', 
                                       period_id=period_id,
                                       team_id=team_id))
    
    # Get base metrics and existing values
    base_metrics = []
    existing_values = {}
    previous_period = None
    previous_values = {}
    previous_values_with_targets = {}
    can_use_blend_report = False
    blend_report_values = {}
    
    if user_team and selected_period:
        base_metrics = MetricsService.get_base_metrics_for_team(user_team.id)
        existing_values = MetricsService.get_metric_values_with_targets(user_team.id, selected_period.id)
        previous_period = get_previous_period(selected_period)
        if previous_period:
            previous_values = MetricsService.get_metric_values(user_team.id, previous_period.id)
            previous_values_with_targets = MetricsService.get_metric_values_with_targets(user_team.id, previous_period.id)

        for metric in base_metrics:
            current_entry = existing_values.get(metric.key)
            previous_config = _target_config_from_entry(previous_values_with_targets.get(metric.key))
            if not _target_config_has_values(previous_config):
                continue

            if current_entry is None:
                existing_values[metric.key] = {
                    'value': '',
                    **previous_config,
                }
                continue

            current_config = _target_config_from_entry(current_entry)
            if not _target_config_has_values(current_config):
                current_entry.update(previous_config)
                current_value = current_entry.get('value')
                if current_value is not None:
                    MetricsService.save_metric_value_with_target(
                        metric.id,
                        user_team.id,
                        selected_period.id,
                        current_value,
                        previous_config.get('target'),
                        previous_config.get('target_type', 'single'),
                        previous_config.get('target_lower'),
                        previous_config.get('target_upper'),
                    )

        blend_report_user_id = AppSetting.get_value(BLEND_REPORT_SETTING_KEY)
        can_use_blend_report = (
            AccessService.can_access_page(current_user, 'reporting_input', 'edit')
            and blend_report_user_id
            and str(current_user.id) == str(blend_report_user_id)
        )
        if can_use_blend_report:
            for metric in base_metrics:
                previous_value = previous_values.get(metric.key)
                if previous_value is None:
                    continue
                try:
                    blend_report_values[str(metric.id)] = _blend_report_value(previous_value)
                except (TypeError, ValueError):
                    continue
    
    return render_template('reporting/input.html',
                          periods=periods,
                          teams=teams,
                          selected_period=selected_period,
                          previous_period=previous_period,
                          user_team=user_team,
                          base_metrics=base_metrics,
                          existing_values=existing_values,
                          previous_values=previous_values,
                          is_admin=current_user.is_admin(),
                          can_use_blend_report=can_use_blend_report,
                          blend_report_values=blend_report_values)


@reporting_bp.route('/output')
@login_required
@require_page_permission('reporting_output')
def output():
    """
    Results/output page showing all metrics for a period.
    """
    # Results start from the previous completed week and continue backward.
    periods = _weekly_period_window()[1:]
    teams = MetricsService.get_all_teams()
    
    # Get selected team
    team_id = request.args.get('team_id', type=int)
    selected_team = None
    
    if team_id:
        selected_team = MetricsService.get_team_by_id(team_id)
    elif current_user.team:
        selected_team = current_user.team
    elif teams and current_user.is_admin():
        selected_team = teams[0]
    
    # Get selected period
    period_id = request.args.get('period_id', type=int)
    selected_period = None
    
    if period_id:
        selected_period = MetricsService.get_period_by_id(period_id)
        if selected_period and selected_period.id not in {period.id for period in periods}:
            selected_period = None
    if not selected_period and periods:
        selected_period = periods[0]
    
    # Build results
    base_results = []
    derived_results = []
    base_grouped = OrderedDict()
    previous_period = None
    history_periods = []
    
    if selected_team and selected_period:
        previous_period = (ReportingPeriod.query
                           .filter(ReportingPeriod.period_type == selected_period.period_type)
                           .filter(ReportingPeriod.start_date < selected_period.start_date)
                           .order_by(ReportingPeriod.start_date.desc())
                           .first())

        history_periods = (ReportingPeriod.query
                           .filter(ReportingPeriod.period_type == selected_period.period_type)
                           .filter(ReportingPeriod.start_date < selected_period.start_date)
                           .order_by(ReportingPeriod.start_date.desc())
                           .limit(3)
                           .all())
        # Keep newest-to-oldest ordering for display

        # Get base metric values
        base_values_with_targets = MetricsService.get_metric_values_with_targets(selected_team.id, selected_period.id)
        base_values = MetricsService.get_metric_values(selected_team.id, selected_period.id)
        prev_base_values = MetricsService.get_metric_values(selected_team.id, previous_period.id) if previous_period else {}
        base_metrics = MetricsService.get_base_metrics_for_team(selected_team.id)

        history_base_values = [
            MetricsService.get_metric_values(selected_team.id, p.id)
            for p in history_periods
        ]

        # Calculate derived metrics
        derived_metrics = MetricsService.get_derived_metrics_for_team(selected_team.id)
        derived_values = FormulaService.compute_derived_metrics(base_values, derived_metrics)
        prev_derived_values = FormulaService.compute_derived_metrics(prev_base_values, derived_metrics) if previous_period else {}

        history_derived_values = [
            FormulaService.compute_derived_metrics(history_base_values[i], derived_metrics)
            for i in range(len(history_periods))
        ]

        def compute_delta(current_value, previous_value):
            if current_value is None or previous_value is None:
                return None
            try:
                prev = float(previous_value)
                curr = float(current_value)
            except (TypeError, ValueError):
                return None
            if prev == 0:
                return None
            return ((curr - prev) / prev) * 100.0

        def classify_delta(delta_pct, trend_direction):
            if delta_pct is None:
                return 'neutral'
            if abs(delta_pct) < 1e-12:
                return 'neutral'
            if trend_direction == 'higher_is_better':
                return 'good' if delta_pct > 0 else 'bad'
            if trend_direction == 'lower_is_better':
                return 'good' if delta_pct < 0 else 'bad'
            return 'neutral'

        def target_config(target_type, target, target_lower, target_upper):
            return {
                'target_type': target_type if target_type in ('single', 'range') else 'single',
                'target': target,
                'target_lower': target_lower,
                'target_upper': target_upper,
            }

        def has_target(config):
            return _target_config_has_values(config)

        def target_threshold_for_progress(config, trend_direction):
            if not has_target(config):
                return None
            if config.get('target_type') == 'range':
                if trend_direction == 'higher_is_better':
                    return config.get('target_lower')
                return config.get('target_upper')
            return config.get('target')

        def classify_target_delta(value, config, trend_direction):
            if value is None or not has_target(config):
                return 'neutral'
            try:
                v = float(value)
            except (TypeError, ValueError):
                return 'neutral'

            if config.get('target_type') == 'range':
                lower = float(config.get('target_lower'))
                upper = float(config.get('target_upper'))
                if lower <= v <= upper:
                    return 'good'
                if trend_direction == 'higher_is_better':
                    return 'good' if v > upper else 'bad'
                if trend_direction == 'lower_is_better':
                    return 'good' if v < lower else 'bad'
                return 'bad'

            t = config.get('target')
            if t is None:
                return 'neutral'
            t = float(t)
            if trend_direction == 'higher_is_better':
                return 'good' if v >= t else 'bad'
            if trend_direction == 'lower_is_better':
                return 'good' if v <= t else 'bad'
            return 'good' if v <= t else 'bad'

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

        def range_card_presentation(value, config, trend_direction, target_status):
            fallback_color = 'red' if target_status == 'bad' else 'green'
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

        def compute_goal_status(value, config, trend_direction):
            target_status = classify_target_delta(value, config, trend_direction)
            if target_status == 'neutral':
                return None
            return 'achieved' if target_status == 'good' else 'not_achieved'

        def compute_target_delta(value, config, trend_direction):
            threshold = target_threshold_for_progress(config, trend_direction)
            if value is None or threshold is None:
                return None, None
            try:
                v = float(value)
                t = float(threshold)
            except (TypeError, ValueError):
                return None, None
            diff = v - t
            pct = None
            if abs(t) > 1e-12:
                pct = (diff / t) * 100.0
            return diff, pct

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

        def format_target_label(config, unit):
            if not has_target(config):
                return None
            if config.get('target_type') == 'range':
                lower = FormulaService.format_value(config.get('target_lower'), unit)
                upper = FormulaService.format_value(config.get('target_upper'), unit)
                return f'{lower} - {upper}'
            return FormulaService.format_value(config.get('target'), unit)

        def compute_ring_offset(progress_pct):
            circumference = 427.26
            return circumference - ((progress_pct or 0) / 100.0) * circumference

        def split_metric_name(display_name):
            parts = (display_name or '').strip().split(' ', 1)
            subject = parts[0] if parts and parts[0] else 'Metric'
            title = parts[1] if len(parts) > 1 else display_name
            return subject, title

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
                if v < lower:
                    diff = v - lower
                else:
                    diff = v - upper
            else:
                diff = v - float(config.get('target'))
                if abs(diff) < 1e-12:
                    return None

            formatted = FormulaService.format_value(abs(diff), 'number')
            if trend_direction == 'higher_is_better':
                return f'+{formatted} above' if diff > 0 else f'-{formatted} under'
            return f'+{formatted} over' if diff > 0 else f'-{formatted} under'

        def format_previous_delta(value, previous_value):
            if value is None or previous_value is None:
                return 'No previous data'
            try:
                diff = float(value) - float(previous_value)
            except (TypeError, ValueError):
                return 'No previous data'
            if abs(diff) < 1e-12:
                return 'No change from last week'
            formatted = FormulaService.format_value(abs(diff), 'number')
            sign = '+' if diff > 0 else '-'
            return f'{sign}{formatted} from last week'

        def status_label(target_delta_status, trend_direction):
            if target_delta_status == 'neutral':
                return 'No limit'
            if target_delta_status == 'good':
                return 'Within target' if trend_direction != 'higher_is_better' else 'Target met'
            if trend_direction == 'higher_is_better':
                return 'Below target'
            return 'Over limit'

        for metric in base_metrics:
            entry = base_values_with_targets.get(metric.key) or {}
            value = entry.get('value')
            target = entry.get('target')
            target_type = entry.get('target_type') or 'single'
            target_lower = entry.get('target_lower')
            target_upper = entry.get('target_upper')
            target_cfg = target_config(target_type, target, target_lower, target_upper)
            prev_value = prev_base_values.get(metric.key)
            trend_direction = getattr(metric, 'trend_direction', 'neutral')
            delta_pct = compute_delta(value, prev_value)
            target_diff, target_diff_pct = compute_target_delta(value, target_cfg, trend_direction)
            target_delta_status = classify_target_delta(value, target_cfg, trend_direction)
            limit_progress_pct = compute_limit_progress_pct(value, target_cfg, trend_direction)
            limit_ratio_pct = compute_limit_ratio_pct(value, target_cfg, trend_direction)
            subject_label, metric_title = split_metric_name(metric.display_name)
            has_target_value = has_target(target_cfg)
            ratio_label = f'{limit_ratio_pct:.0f}% of limit' if limit_ratio_pct is not None else 'No limit'
            if target_type == 'range' and has_target_value:
                ratio_label = 'In target range' if target_delta_status == 'good' else 'Outside range'
            card_color, card_style = range_card_presentation(
                value,
                target_cfg,
                trend_direction,
                target_delta_status,
            )

            history = []
            for idx, p in enumerate(history_periods):
                hv = history_base_values[idx].get(metric.key)
                history.append({
                    'period': p,
                    'value': hv,
                    'formatted': FormulaService.format_value(hv, metric.unit) if hv is not None else 'Null'
                })

            base_results.append({
                'metric': metric,
                'value': value,
                'target': target,
                'target_type': target_type,
                'target_lower': target_lower,
                'target_upper': target_upper,
                'has_target': has_target_value,
                'goal_status': compute_goal_status(value, target_cfg, getattr(metric, 'trend_direction', 'neutral')),
                'target_formatted': format_target_label(target_cfg, metric.unit),
                'target_diff': target_diff,
                'target_diff_pct': target_diff_pct,
                'target_delta_status': target_delta_status,
                'card_color': card_color,
                'card_style': card_style,
                'status_label': status_label(target_delta_status, trend_direction),
                'subject_label': subject_label,
                'subject_initial': subject_label[:1].upper(),
                'metric_title': metric_title,
                'achievement_stars': compute_achievement_stars(value, target_cfg, trend_direction),
                'limit_progress_pct': limit_progress_pct,
                'limit_ratio_pct': limit_ratio_pct,
                'ring_offset': compute_ring_offset(limit_progress_pct),
                'ratio_label': ratio_label,
                'limit_delta_label': format_limit_difference(value, target_cfg, trend_direction),
                'previous_delta_label': format_previous_delta(value, prev_value),
                'period_label': selected_period.label if selected_period else '',
                'prev_value': prev_value,
                'delta_pct': delta_pct,
                'delta_status': classify_delta(delta_pct, trend_direction),
                'formatted': FormulaService.format_value(value, metric.unit) if value is not None else 'N/A',
                'history': history
            })

        for item in base_results:
            metric = item.get('metric')
            category_name = getattr(getattr(metric, 'category', None), 'name', None) or 'Uncategorized'
            sub_category_name = getattr(getattr(metric, 'sub_category', None), 'name', None) or 'Uncategorized'
            if category_name not in base_grouped:
                base_grouped[category_name] = OrderedDict()
            if sub_category_name not in base_grouped[category_name]:
                base_grouped[category_name][sub_category_name] = []
            base_grouped[category_name][sub_category_name].append(item)

        base_grouped_sorted = OrderedDict()
        for cat in sorted(base_grouped.keys()):
            subs = base_grouped[cat]
            subs_sorted = OrderedDict()
            for sub in sorted(subs.keys()):
                subs_sorted[sub] = subs[sub]
            base_grouped_sorted[cat] = subs_sorted
        base_grouped = base_grouped_sorted
        
        for metric in derived_metrics:
            value = derived_values.get(metric.key)
            prev_value = prev_derived_values.get(metric.key) if previous_period else None
            delta_pct = compute_delta(value, prev_value)

            history = []
            for idx, p in enumerate(history_periods):
                hv = history_derived_values[idx].get(metric.key)
                history.append({
                    'period': p,
                    'value': hv,
                    'formatted': FormulaService.format_value(hv, metric.unit) if hv is not None else 'Null'
                })

            derived_results.append({
                'metric': metric,
                'value': value,
                'prev_value': prev_value,
                'delta_pct': delta_pct,
                'delta_status': classify_delta(delta_pct, getattr(metric, 'trend_direction', 'neutral')),
                'formatted': FormulaService.format_value(value, metric.unit) if value is not None else 'N/A',
                'history': history
            })
    
    return render_template('reporting/output.html',
                          periods=periods,
                          teams=teams,
                          selected_period=selected_period,
                          previous_period=previous_period,
                          selected_team=selected_team,
                          base_results=base_results,
                          base_grouped=base_grouped,
                          derived_results=derived_results,
                          is_admin=current_user.is_admin())
