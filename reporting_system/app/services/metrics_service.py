"""
Metrics service for fetching and saving metric values.
"""
from datetime import date, timedelta
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from ..models.metric import MetricDefinition, MetricValue, ReportingPeriod, MetricCategory, MetricSubCategory
from ..models.team import Team
from ..extensions import db
from .formula_service import FormulaService


class MetricsService:
    """Service class for metric operations."""

    @staticmethod
    def _allowed_team_ids_for_user(user):
        if user is None:
            return []

        is_admin = getattr(user, 'is_admin', None)
        if callable(is_admin) and is_admin():
            return None
        if getattr(user, 'role', None) == 'admin':
            return None

        team_id = getattr(user, 'team_id', None)
        if team_id:
            return [team_id]

        dept = (getattr(user, 'role', None) or '').strip() or None
        if not dept:
            return []

        teams = Team.query.filter(or_(Team.type == dept, Team.name == dept)).all()
        return [t.id for t in teams]

    @staticmethod
    def get_all_teams_for_user(user):
        allowed_ids = MetricsService._allowed_team_ids_for_user(user)
        query = Team.query
        if allowed_ids is not None:
            if not allowed_ids:
                return []
            query = query.filter(Team.id.in_(allowed_ids))
        return query.order_by(Team.name).all()

    @staticmethod
    def get_all_metrics_for_user(user, include_inactive=False):
        allowed_ids = MetricsService._allowed_team_ids_for_user(user)

        query = MetricDefinition.query.options(
            joinedload(MetricDefinition.team),
            selectinload(MetricDefinition.scoped_teams),
            joinedload(MetricDefinition.category),
            joinedload(MetricDefinition.sub_category),
        )
        if not include_inactive:
            query = query.filter_by(active=True)

        if allowed_ids is None:
            return query.order_by(MetricDefinition.layer, MetricDefinition.display_name).all()
        if not allowed_ids:
            return query.filter(MetricDefinition.scope == 'global').order_by(MetricDefinition.layer, MetricDefinition.display_name).all()

        return (
            query.filter(
                or_(
                    MetricDefinition.scope == 'global',
                    MetricDefinition.team_id.in_(allowed_ids),
                    MetricDefinition.scoped_teams.any(Team.id.in_(allowed_ids)),
                )
            )
            .order_by(MetricDefinition.layer, MetricDefinition.display_name)
            .all()
        )

    @staticmethod
    def _link_category_to_teams(category, team_ids):
        if not category or not team_ids:
            return
        teams = Team.query.filter(Team.id.in_(team_ids)).all()
        existing_ids = {t.id for t in category.teams}
        for t in teams:
            if t.id not in existing_ids:
                category.teams.append(t)

    @staticmethod
    def _normalize_category_name(name):
        if name is None:
            return None
        name = str(name).strip()
        return name or None

    @staticmethod
    def _get_or_create_category(name):
        name = MetricsService._normalize_category_name(name)
        if not name:
            return None
        category = MetricCategory.query.filter_by(name=name).first()
        if category is None:
            category = MetricCategory(name=name)
            db.session.add(category)
            db.session.flush()
        return category

    @staticmethod
    def _get_or_create_sub_category(category, name):
        name = MetricsService._normalize_category_name(name)
        if not category or not name:
            return None
        sub_category = MetricSubCategory.query.filter_by(category_id=category.id, name=name).first()
        if sub_category is None:
            sub_category = MetricSubCategory(category_id=category.id, name=name)
            db.session.add(sub_category)
            db.session.flush()
        return sub_category

    @staticmethod
    def get_all_category_names():
        return [c.name for c in MetricCategory.query.order_by(MetricCategory.name).all()]

    @staticmethod
    def get_sub_category_names_for_category(category_name):
        category_name = MetricsService._normalize_category_name(category_name)
        if not category_name:
            return []
        category = MetricCategory.query.filter_by(name=category_name).first()
        if not category:
            return []
        return [
            sc.name
            for sc in MetricSubCategory.query.filter_by(category_id=category.id)
            .order_by(MetricSubCategory.name)
            .all()
        ]

    @staticmethod
    def create_category(name):
        category = MetricsService._get_or_create_category(name)
        if category is None:
            raise ValueError('Category name is required.')
        db.session.commit()
        return category

    @staticmethod
    def create_sub_category(category_name, sub_category_name):
        category = MetricsService._get_or_create_category(category_name)
        if category is None:
            raise ValueError('Category is required.')
        sub_category = MetricsService._get_or_create_sub_category(category, sub_category_name)
        if sub_category is None:
            raise ValueError('Sub category name is required.')
        db.session.commit()
        return sub_category

    @staticmethod
    def get_all_categories_with_sub_categories():
        return (
            MetricCategory.query.options(joinedload(MetricCategory.sub_categories))
            .order_by(MetricCategory.name)
            .all()
        )

    @staticmethod
    def get_all_categories_with_sub_categories_for_user(user):
        allowed_ids = MetricsService._allowed_team_ids_for_user(user)

        categories = (
            MetricCategory.query.options(
                joinedload(MetricCategory.sub_categories),
                joinedload(MetricCategory.teams),
            )
            .order_by(MetricCategory.name)
            .all()
        )

        if allowed_ids is None:
            return categories
        if not allowed_ids:
            return [c for c in categories if not c.teams]

        return [
            c for c in categories
            if (not c.teams) or any(t.id in allowed_ids for t in c.teams)
        ]

    @staticmethod
    def get_all_sub_categories_with_categories():
        return (
            MetricSubCategory.query.options(joinedload(MetricSubCategory.category))
            .join(MetricCategory, MetricCategory.id == MetricSubCategory.category_id)
            .order_by(MetricCategory.name, MetricSubCategory.name)
            .all()
        )

    @staticmethod
    def get_all_sub_categories_with_categories_for_user(user):
        allowed_ids = MetricsService._allowed_team_ids_for_user(user)

        sub_categories = (
            MetricSubCategory.query.options(
                joinedload(MetricSubCategory.category).joinedload(MetricCategory.teams),
            )
            .join(MetricCategory, MetricCategory.id == MetricSubCategory.category_id)
            .order_by(MetricCategory.name, MetricSubCategory.name)
            .all()
        )

        if allowed_ids is None:
            return sub_categories
        if not allowed_ids:
            return [sc for sc in sub_categories if sc.category and not sc.category.teams]

        return [
            sc for sc in sub_categories
            if sc.category and ((not sc.category.teams) or any(t.id in allowed_ids for t in sc.category.teams))
        ]

    @staticmethod
    def get_all_category_names_for_user(user):
        categories = MetricsService.get_all_categories_with_sub_categories_for_user(user)
        return [c.name for c in categories]

    @staticmethod
    def get_sub_category_names_for_category_for_user(user, category_name):
        category_name = MetricsService._normalize_category_name(category_name)
        if not category_name:
            return []

        allowed_ids = MetricsService._allowed_team_ids_for_user(user)

        category = MetricCategory.query.options(joinedload(MetricCategory.teams)).filter_by(name=category_name).first()
        if not category:
            return []

        if allowed_ids is not None:
            if category.teams and not any(t.id in allowed_ids for t in category.teams):
                return []
            if (not allowed_ids) and category.teams:
                return []

        return [
            sc.name
            for sc in MetricSubCategory.query.filter_by(category_id=category.id)
            .order_by(MetricSubCategory.name)
            .all()
        ]

    @staticmethod
    def rename_category(category_id: int, new_name: str):
        new_name = MetricsService._normalize_category_name(new_name)
        if not new_name:
            raise ValueError('Category name is required.')

        category = MetricCategory.query.get(category_id)
        if not category:
            raise ValueError('Category not found.')

        category.name = new_name
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('Category name already exists.')
        return category

    @staticmethod
    def rename_sub_category(sub_category_id: int, new_name: str):
        new_name = MetricsService._normalize_category_name(new_name)
        if not new_name:
            raise ValueError('Sub category name is required.')

        sub_category = MetricSubCategory.query.get(sub_category_id)
        if not sub_category:
            raise ValueError('Sub category not found.')

        sub_category.name = new_name
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('Sub category name already exists for this category.')
        return sub_category

    @staticmethod
    def delete_category(category_id: int):
        category = MetricCategory.query.get(category_id)
        if not category:
            return False, 'Category not found.'

        referenced = MetricDefinition.query.filter_by(category_id=category_id).first() is not None
        if referenced:
            return False, 'Cannot delete category: it is referenced by one or more metrics.'

        category.teams = []
        db.session.delete(category)
        db.session.commit()
        return True, 'Category deleted.'

    @staticmethod
    def delete_sub_category(sub_category_id: int):
        sub_category = MetricSubCategory.query.get(sub_category_id)
        if not sub_category:
            return False, 'Sub category not found.'

        referenced = MetricDefinition.query.filter_by(sub_category_id=sub_category_id).first() is not None
        if referenced:
            return False, 'Cannot delete sub category: it is referenced by one or more metrics.'

        db.session.delete(sub_category)
        db.session.commit()
        return True, 'Sub category deleted.'
    
    @staticmethod
    def get_all_metrics(include_inactive=False):
        """
        Get all metric definitions.
        
        Args:
            include_inactive: Whether to include inactive metrics
            
        Returns:
            List of MetricDefinition instances
        """
        query = MetricDefinition.query
        if not include_inactive:
            query = query.filter_by(active=True)
        return query.order_by(MetricDefinition.layer, MetricDefinition.display_name).all()
    
    @staticmethod
    def get_metric_by_id(metric_id):
        """Get a metric definition by ID."""
        return MetricDefinition.query.get(metric_id)
    
    @staticmethod
    def get_metric_by_key(key):
        """Get a metric definition by key."""
        return MetricDefinition.query.filter_by(key=key).first()
    
    @staticmethod
    def create_metric(key, display_name, unit='number', scope='global', 
                      team_id=None, is_derived=False, formula=None, 
                      layer=1, description=None, trend_direction='neutral', team_ids=None,
                      category=None, sub_category=None):
        """
        Create a new metric definition.
        
        Args:
            key: Unique slug identifier
            display_name: Human-readable name
            unit: Unit of measurement
            scope: Metric scope (global or team)
            team_id: Optional team ID for team-specific metrics
            is_derived: Whether metric is calculated from formula
            formula: Formula string for derived metrics
            layer: Layer number (1 for base, 2+ for derived)
            description: Optional description
            
        Returns:
            New MetricDefinition instance
        """
        if team_ids:
            scope = 'team'
            team_id = None

        category_obj = MetricsService._get_or_create_category(category)
        sub_category_obj = MetricsService._get_or_create_sub_category(category_obj, sub_category)

        if team_ids:
            MetricsService._link_category_to_teams(category_obj, team_ids)

        metric = MetricDefinition(
            key=key,
            display_name=display_name,
            trend_direction=trend_direction,
            unit=unit,
            scope=scope,
            team_id=team_id,
            category_id=category_obj.id if category_obj else None,
            sub_category_id=sub_category_obj.id if sub_category_obj else None,
            is_derived=is_derived,
            formula=formula,
            layer=layer,
            description=description,
            active=True
        )

        if team_ids:
            metric.scoped_teams = Team.query.filter(Team.id.in_(team_ids)).all()

        db.session.add(metric)
        db.session.commit()
        return metric
    
    @staticmethod
    def update_metric(metric_id, **kwargs):
        """
        Update a metric definition.
        
        Args:
            metric_id: Metric ID to update
            **kwargs: Fields to update
            
        Returns:
            Updated MetricDefinition instance or None
        """
        metric = MetricDefinition.query.get(metric_id)
        if metric:
            team_ids_for_category = None
            scoped_teams = kwargs.get('scoped_teams')
            if scoped_teams is not None:
                team_ids_for_category = [t.id for t in scoped_teams]
            if 'category' in kwargs or 'sub_category' in kwargs:
                category_name = kwargs.pop('category', None)
                sub_category_name = kwargs.pop('sub_category', None)
                category_obj = MetricsService._get_or_create_category(category_name)
                sub_category_obj = MetricsService._get_or_create_sub_category(category_obj, sub_category_name)
                metric.category_id = category_obj.id if category_obj else None
                metric.sub_category_id = sub_category_obj.id if sub_category_obj else None
                if team_ids_for_category:
                    MetricsService._link_category_to_teams(category_obj, team_ids_for_category)
            for key, value in kwargs.items():
                if hasattr(metric, key):
                    setattr(metric, key, value)
            db.session.commit()
        return metric
    
    @staticmethod
    def delete_metric(metric_id):
        """
        Delete a metric definition (soft delete by setting active=False).
        
        Args:
            metric_id: Metric ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        metric = MetricDefinition.query.get(metric_id)
        if metric:
            return MetricsService.set_metric_active(metric_id, False)
        return False

    @staticmethod
    def set_metric_active(metric_id, active: bool):
        """Set metric active state."""
        metric = MetricDefinition.query.get(metric_id)
        if not metric:
            return False
        metric.active = bool(active)
        db.session.commit()
        return True

    @staticmethod
    def metric_has_values(metric_id) -> bool:
        """Return True if the metric has any MetricValue rows."""
        return MetricValue.query.filter_by(metric_id=metric_id).first() is not None

    @staticmethod
    def metric_is_referenced(metric_id) -> bool:
        """Return True if any derived metric formula references this metric's key."""
        metric = MetricDefinition.query.get(metric_id)
        if not metric:
            return False
        metric_key = metric.key
        derived_metrics = MetricDefinition.query.filter_by(is_derived=True).all()
        for derived in derived_metrics:
            if not derived.formula:
                continue
            referenced = FormulaService.extract_metric_keys(derived.formula)
            if metric_key in referenced and derived.id != metric_id:
                return True
        return False

    @staticmethod
    def delete_metric_permanently(metric_id):
        """Hard delete a metric definition if safe.

        Returns:
            (success: bool, message: str)
        """
        metric = MetricDefinition.query.get(metric_id)
        if not metric:
            return False, 'Metric not found.'

        if MetricsService.metric_is_referenced(metric_id):
            return False, 'Cannot permanently delete: metric is referenced by a derived metric formula.'

        deleted_values = (MetricValue.query
                          .filter_by(metric_id=metric_id)
                          .delete(synchronize_session=False))

        db.session.delete(metric)
        db.session.commit()
        return True, f'Metric permanently deleted (removed {deleted_values} value(s)).'
    
    @staticmethod
    def get_base_metrics_for_team(team_id):
        """
        Get all base (layer 1) metrics applicable to a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of MetricDefinition instances
        """
        return MetricDefinition.get_base_metrics(team_id)
    
    @staticmethod
    def get_derived_metrics_for_team(team_id):
        """
        Get all derived metrics applicable to a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of MetricDefinition instances
        """
        return MetricDefinition.get_derived_metrics(team_id)
    
    @staticmethod
    def save_metric_value(metric_id, team_id, reporting_period_id, value):
        """
        Save or update a metric value.
        
        Args:
            metric_id: Metric definition ID
            team_id: Team ID
            reporting_period_id: Reporting period ID
            value: Numeric value
            
        Returns:
            MetricValue instance
        """
        metric_value = MetricValue.get_or_create(metric_id, team_id, reporting_period_id)
        metric_value.value = value
        db.session.add(metric_value)
        db.session.commit()
        return metric_value

    @staticmethod
    def save_metric_value_with_target(metric_id, team_id, reporting_period_id, value, target=None):
        """Save or update a metric value (and optional target)."""
        metric_value = MetricValue.get_or_create(metric_id, team_id, reporting_period_id)
        metric_value.value = value
        metric_value.target = target
        db.session.add(metric_value)
        db.session.commit()
        return metric_value
    
    @staticmethod
    def get_metric_values(team_id, reporting_period_id):
        """
        Get all metric values for a team and period.
        
        Args:
            team_id: Team ID
            reporting_period_id: Reporting period ID
            
        Returns:
            Dictionary mapping metric keys to values
        """
        return MetricValue.get_values_for_period(team_id, reporting_period_id)

    @staticmethod
    def get_metric_values_with_targets(team_id, reporting_period_id):
        """Get all metric values (and optional targets) for a team and period."""
        return MetricValue.get_values_and_targets_for_period(team_id, reporting_period_id)
    
    @staticmethod
    def get_metric_value_objects(team_id, reporting_period_id):
        """
        Get all MetricValue objects for a team and period.
        
        Args:
            team_id: Team ID
            reporting_period_id: Reporting period ID
            
        Returns:
            List of MetricValue instances
        """
        return MetricValue.query.filter_by(
            team_id=team_id,
            reporting_period_id=reporting_period_id
        ).all()
    
    # Reporting Period methods
    
    @staticmethod
    def get_all_periods():
        """Get all reporting periods ordered by start date descending."""
        return ReportingPeriod.query.order_by(ReportingPeriod.start_date.desc()).all()
    
    @staticmethod
    def get_period_by_id(period_id):
        """Get a reporting period by ID."""
        return ReportingPeriod.query.get(period_id)
    
    @staticmethod
    def get_recent_periods(limit=10):
        """Get most recent reporting periods."""
        periods = ReportingPeriod.get_recent(limit)
        if periods:
            return periods

        MetricsService.ensure_weekly_periods_for_current_year(start_week=40)
        return ReportingPeriod.get_recent(limit)
    
    @staticmethod
    def create_period(period_type, start_date, end_date, label):
        """
        Create a new reporting period.
        
        Args:
            period_type: Type of period (weekly, monthly, etc.)
            start_date: Period start date
            end_date: Period end date
            label: Human-readable label
            
        Returns:
            New ReportingPeriod instance
        """
        period = ReportingPeriod(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            label=label
        )
        db.session.add(period)
        db.session.commit()
        return period
    
    @staticmethod
    def generate_weekly_label(start_date):
        """
        Generate a weekly period label from a start date.
        
        Args:
            start_date: Period start date
            
        Returns:
            Label string (e.g., "2025-W48")
        """
        year, week, _ = start_date.isocalendar()
        return f"{year}-W{week:02d}"
    
    @staticmethod
    def generate_monthly_label(start_date):
        """
        Generate a monthly period label from a start date.
        
        Args:
            start_date: Period start date
            
        Returns:
            Label string (e.g., "2025-12")
        """
        return start_date.strftime("%Y-%m")
    
    @staticmethod
    def ensure_weekly_periods_for_current_year(start_week: int = 40):
        """
        Ensure weekly reporting periods exist from a given ISO week number up to next week
        of the current year. If a period is missing, create it with correct start/end dates
        and label.
        """
        today = date.today()
        iso_year, iso_week, _ = today.isocalendar()

        def _ensure_weekly_periods_for_iso_year(target_iso_year: int, week_start: int, week_end: int):
            if week_start > week_end:
                return

            for w in range(week_start, week_end + 1):
                try:
                    start_date = date.fromisocalendar(target_iso_year, w, 1)  # Monday
                except ValueError:
                    continue
                end_date = start_date + timedelta(days=6)
                label = MetricsService.generate_weekly_label(start_date)

                existing = ReportingPeriod.query.filter_by(label=label).first()
                if existing:
                    continue

                MetricsService.create_period(
                    period_type='weekly',
                    start_date=start_date,
                    end_date=end_date,
                    label=label,
                )

        # If we're early in the ISO year (e.g. week 1) and start_week is 40,
        # the desired range spans the previous ISO year and the current ISO year.
        # Example: today=2025-12-29 might be ISO year 2026, week 1.
        target_last_week = min(iso_week + 1, 53)

        if iso_week < start_week:
            _ensure_weekly_periods_for_iso_year(iso_year - 1, start_week, 53)
            _ensure_weekly_periods_for_iso_year(iso_year, 1, target_last_week)
        else:
            _ensure_weekly_periods_for_iso_year(iso_year, start_week, target_last_week)
    
    # Team methods
    
    @staticmethod
    def get_all_teams():
        """Get all teams."""
        return Team.query.order_by(Team.name).all()
    
    @staticmethod
    def get_team_by_id(team_id):
        """Get a team by ID."""
        return Team.query.get(team_id)
