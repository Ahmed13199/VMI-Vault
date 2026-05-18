"""
Metric-related models: MetricDefinition, MetricValue, ReportingPeriod.
"""
from ..extensions import db


metric_definition_teams = db.Table(
    'metric_definition_teams',
    db.Column('metric_definition_id', db.Integer, db.ForeignKey('metric_definitions.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
)


metric_category_teams = db.Table(
    'metric_category_teams',
    db.Column('category_id', db.Integer, db.ForeignKey('metric_categories.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
)


class MetricCategory(db.Model):
    __tablename__ = 'metric_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True, index=True)

    sub_categories = db.relationship('MetricSubCategory', back_populates='category', cascade='all, delete-orphan')
    metrics = db.relationship('MetricDefinition', back_populates='category')
    teams = db.relationship('Team', secondary='metric_category_teams', back_populates='metric_categories')

    def __repr__(self):
        return f'<MetricCategory {self.name}>'


class MetricSubCategory(db.Model):
    __tablename__ = 'metric_sub_categories'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('metric_categories.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('category_id', 'name', name='uq_metric_sub_category_category_name'),
    )

    category = db.relationship('MetricCategory', back_populates='sub_categories')
    metrics = db.relationship('MetricDefinition', back_populates='sub_category')

    def __repr__(self):
        return f'<MetricSubCategory {self.category_id}:{self.name}>'


class ReportingPeriod(db.Model):
    """
    Reporting period model representing time periods for metrics.
    
    Attributes:
        id: Primary key
        period_type: Type of period (weekly, monthly, etc.)
        start_date: Period start date
        end_date: Period end date
        label: Human-readable label (e.g., "2025-W48")
    """
    __tablename__ = 'reporting_periods'
    
    id = db.Column(db.Integer, primary_key=True)
    period_type = db.Column(db.String(16), nullable=False, default='weekly')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    label = db.Column(db.String(32), nullable=False)
    
    # Relationships
    metric_values = db.relationship('MetricValue', back_populates='reporting_period', lazy='dynamic')
    
    # Valid period types
    PERIOD_TYPES = ['weekly', 'monthly', 'quarterly', 'yearly']
    
    def __repr__(self):
        return f'<ReportingPeriod {self.label}>'
    
    @classmethod
    def get_recent(cls, limit=10):
        """Get most recent reporting periods."""
        return cls.query.order_by(cls.start_date.desc()).limit(limit).all()


class MetricDefinition(db.Model):
    """
    Metric definition model for both base and derived metrics.
    
    Attributes:
        id: Primary key
        key: Unique slug identifier (e.g., "total_calls", "missed_calls_pct")
        display_name: Human-readable name
        description: Optional description
        trend_direction: Trend direction (neutral, higher_is_better, lower_is_better)
        unit: Unit of measurement (number, percent, currency, hours)
        scope: Metric scope (global or team-specific)
        team_id: Optional FK to Team if metric is team-specific
        category_id: Optional FK to MetricCategory
        sub_category_id: Optional FK to MetricSubCategory
        is_derived: True if metric is calculated from formula
        formula: Formula string for derived metrics
        active: Whether metric is active
        layer: Layer number (1 for base, 2+ for derived)
    """
    __tablename__ = 'metric_definitions'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    trend_direction = db.Column(db.String(32), nullable=False, default='neutral')
    unit = db.Column(db.String(32), nullable=False, default='number')
    scope = db.Column(db.String(16), nullable=False, default='global')
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('metric_categories.id'), nullable=True, index=True)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('metric_sub_categories.id'), nullable=True, index=True)
    is_derived = db.Column(db.Boolean, nullable=False, default=False)
    formula = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    layer = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    team = db.relationship('Team', back_populates='metric_definitions')
    scoped_teams = db.relationship('Team', secondary='metric_definition_teams', back_populates='scoped_metrics')
    values = db.relationship('MetricValue', back_populates='metric', lazy='dynamic')
    category = db.relationship('MetricCategory', back_populates='metrics')
    sub_category = db.relationship('MetricSubCategory', back_populates='metrics')
    
    # Valid units
    UNITS = ['number', 'percent', 'currency', 'mins', 'days', 'count']

    # Valid trend directions
    TREND_DIRECTIONS = ['neutral', 'higher_is_better', 'lower_is_better']
    
    # Valid scopes
    SCOPES = ['global', 'team']
    
    def __repr__(self):
        return f'<MetricDefinition {self.key}>'
    
    @classmethod
    def get_base_metrics(cls, team_id=None):
        """
        Get all active base (layer 1) metrics.
        
        Args:
            team_id: Optional team ID to filter team-specific metrics
            
        Returns:
            List of base MetricDefinition instances
        """
        query = cls.query.filter_by(is_derived=False, active=True)
        if team_id:
            query = query.filter(
                db.or_(
                    cls.scope == 'global',
                    db.and_(
                        cls.scope == 'team',
                        db.or_(
                            cls.team_id == team_id,
                            cls.scoped_teams.any(id=team_id)
                        )
                    )
                )
            )
        return query.order_by(cls.display_name).all()
    
    @classmethod
    def get_derived_metrics(cls, team_id=None):
        """
        Get all active derived (layer 2+) metrics.
        
        Args:
            team_id: Optional team ID to filter team-specific metrics
            
        Returns:
            List of derived MetricDefinition instances ordered by layer
        """
        query = cls.query.filter_by(is_derived=True, active=True)
        if team_id:
            query = query.filter(
                db.or_(
                    cls.scope == 'global',
                    db.and_(
                        cls.scope == 'team',
                        db.or_(
                            cls.team_id == team_id,
                            cls.scoped_teams.any(id=team_id)
                        )
                    )
                )
            )
        return query.order_by(cls.layer, cls.display_name).all()
    
    @classmethod
    def get_all_active(cls, team_id=None):
        """Get all active metrics ordered by layer."""
        query = cls.query.filter_by(active=True)
        if team_id:
            query = query.filter(
                db.or_(
                    cls.scope == 'global',
                    db.and_(
                        cls.scope == 'team',
                        db.or_(
                            cls.team_id == team_id,
                            cls.scoped_teams.any(id=team_id)
                        )
                    )
                )
            )
        return query.order_by(cls.layer, cls.display_name).all()


class MetricValue(db.Model):
    """
    Metric value model storing actual metric data points.
    
    Attributes:
        id: Primary key
        metric_id: FK to MetricDefinition
        team_id: FK to Team
        reporting_period_id: FK to ReportingPeriod
        value: Numeric value
    """
    __tablename__ = 'metric_values'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_id = db.Column(db.Integer, db.ForeignKey('metric_definitions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    reporting_period_id = db.Column(db.Integer, db.ForeignKey('reporting_periods.id'), nullable=False)
    value = db.Column(db.Numeric(18, 4), nullable=False)
    target = db.Column(db.Numeric(18, 4), nullable=True)
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (
        db.UniqueConstraint('metric_id', 'team_id', 'reporting_period_id', name='uq_metric_team_period'),
    )
    
    # Relationships
    metric = db.relationship('MetricDefinition', back_populates='values')
    team = db.relationship('Team', back_populates='metric_values')
    reporting_period = db.relationship('ReportingPeriod', back_populates='metric_values')
    
    def __repr__(self):
        return f'<MetricValue {self.metric.key}={self.value}>'
    
    @classmethod
    def get_or_create(cls, metric_id, team_id, reporting_period_id):
        """
        Get existing metric value or create a new one.
        
        Args:
            metric_id: Metric definition ID
            team_id: Team ID
            reporting_period_id: Reporting period ID
            
        Returns:
            MetricValue instance
        """
        value = cls.query.filter_by(
            metric_id=metric_id,
            team_id=team_id,
            reporting_period_id=reporting_period_id
        ).first()
        if value is None:
            value = cls(
                metric_id=metric_id,
                team_id=team_id,
                reporting_period_id=reporting_period_id,
                value=0
            )
        return value
    
    @classmethod
    def get_values_for_period(cls, team_id, reporting_period_id):
        """
        Get all metric values for a team and period.
        
        Args:
            team_id: Team ID
            reporting_period_id: Reporting period ID
            
        Returns:
            Dictionary mapping metric keys to values
        """
        values = cls.query.filter_by(
            team_id=team_id,
            reporting_period_id=reporting_period_id
        ).all()
        return {v.metric.key: float(v.value) for v in values}

    @classmethod
    def get_values_and_targets_for_period(cls, team_id, reporting_period_id):
        """Get metric values (and optional targets) for a team and period."""
        values = cls.query.filter_by(
            team_id=team_id,
            reporting_period_id=reporting_period_id
        ).all()
        result = {}
        for v in values:
            result[v.metric.key] = {
                'value': float(v.value) if v.value is not None else None,
                'target': float(v.target) if v.target is not None else None,
            }
        return result
