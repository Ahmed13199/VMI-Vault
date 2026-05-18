"""
Management script for CLI commands.
Provides utilities for database operations, user management, and seeding.

Usage:
    python manage.py seed          - Seed database with sample data
    python manage.py create_user   - Create a new user
    python manage.py list_users    - List all users
"""
import os
import sys
import click
from datetime import date, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, Team, MetricDefinition, MetricValue, ReportingPeriod


# Create app context
app = create_app(os.environ.get('FLASK_CONFIG') or 'default')


@click.group()
def cli():
    """Management commands for the Reporting System."""
    pass


@cli.command()
@click.option('--username', prompt=True, help='Username for the new user')
@click.option('--first-name', prompt=True, help='First name for the new user')
@click.option('--last-name', prompt=True, help='Last name for the new user')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
@click.option('--role', default='experience', type=click.Choice(['experience', 'sales', 'estimation', 'admin']), help='User role')
@click.option('--rank', default='agent', type=click.Choice(['agent', 'senior', 'team_leader', 'admin']), help='User rank')
@click.option('--team', default=None, help='Team name (optional)')
def create_user(username, first_name, last_name, password, role, rank, team):
    """Create a new user."""
    with app.app_context():
        # Check if user already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo(f'Error: User "{username}" already exists.')
            return
        
        # Get team if specified
        team_id = None
        if team:
            team_obj = Team.query.filter_by(name=team).first()
            if team_obj:
                team_id = team_obj.id
            else:
                click.echo(f'Warning: Team "{team}" not found. Creating user without team.')
        
        # Create user
        user = User.create_user(username, password, role, team_id, rank, first_name, last_name)
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'User "{username}" created successfully with role "{role}" and rank "{rank}".')


@cli.command()
def list_users():
    """List all users."""
    with app.app_context():
        users = User.query.all()
        
        if not users:
            click.echo('No users found.')
            return
        
        click.echo(f'\n{"ID":<5} {"Name":<24} {"Username":<20} {"Role":<15} {"Rank":<15} {"Team":<15}')
        click.echo('-' * 98)
        
        for user in users:
            team_name = user.team.name if user.team else '-'
            click.echo(f'{user.id:<5} {user.full_name:<24} {user.username:<20} {user.role:<15} {user.effective_rank():<15} {team_name:<15}')
        
        click.echo(f'\nTotal: {len(users)} user(s)')


@cli.command()
def seed():
    """Seed the database with sample data."""
    with app.app_context():
        click.echo('Seeding database...')
        
        # Create teams
        teams_data = [
            ('Experience', 'experience'),
            ('Sales', 'sales'),
            ('Estimation', 'estimation'),
            ('EOS', 'eos')
        ]
        
        teams = {}
        for name, type_ in teams_data:
            team = Team.query.filter_by(name=name).first()
            if not team:
                team = Team(name=name, type=type_)
                db.session.add(team)
                click.echo(f'  Created team: {name}')
            teams[name] = team
        
        db.session.commit()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User.create_user('admin', 'admin123', 'admin', rank='admin', first_name='System', last_name='Admin')
            db.session.add(admin)
            click.echo('  Created admin user (username: admin, password: admin123)')
        
        # Create sample users for each team
        sample_users = [
            ('Ahmed', 'Tamer', 'ahmedtamer', '1234', 'experience', 'agent', 'Experience'),
            ('Richard', 'Gomez', 'richardgomez', '12345', 'sales', 'senior', 'Sales'),
            ('Mujtaba', 'Khan', 'mujtaba', '123456', 'estimation', 'team_leader', 'Estimation'),
        ]
        
        for first_name, last_name, username, password, role, rank, team_name in sample_users:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User.create_user(username, password, role, teams[team_name].id, rank, first_name, last_name)
                db.session.add(user)
                click.echo(f'  Created user: {username} ({role}, {rank})')
        
        db.session.commit()
        
        # Create base metrics (Layer 1)
        base_metrics = [
            ('total_calls', 'Total Calls', 'number', 'global', None, 'Total number of calls received'),
            ('missed_calls', 'Missed Calls', 'number', 'global', None, 'Number of calls that were not answered'),
            ('tickets_opened', 'Tickets Opened', 'count', 'global', None, 'Number of experience tickets opened'),
            ('tickets_closed', 'Tickets Closed', 'count', 'global', None, 'Number of experience tickets closed'),
            ('revenue', 'Revenue', 'currency', 'team', 'Sales', 'Total revenue generated'),
            ('deals_closed', 'Deals Closed', 'count', 'team', 'Sales', 'Number of deals closed'),
            ('bugs_fixed', 'Bugs Fixed', 'count', 'team', 'Estimation', 'Number of bugs fixed'),
            ('features_shipped', 'Features Shipped', 'count', 'team', 'Estimation', 'Number of features shipped'),
            ('hours_worked', 'Hours Worked', 'mins', 'global', None, 'Total minutes worked'),
        ]
        
        for key, name, unit, scope, team_name, desc in base_metrics:
            metric = MetricDefinition.query.filter_by(key=key).first()
            if not metric:
                team_id = teams[team_name].id if team_name else None
                metric = MetricDefinition(
                    key=key,
                    display_name=name,
                    unit=unit,
                    scope=scope,
                    team_id=team_id,
                    is_derived=False,
                    layer=1,
                    description=desc,
                    active=True
                )
                db.session.add(metric)
                click.echo(f'  Created base metric: {key}')
        
        db.session.commit()
        
        # Create derived metrics (Layer 2)
        derived_metrics = [
            ('missed_calls_pct', 'Missed Calls %', 'percent', 'global', None, 
             'missed_calls / total_calls * 100', 2, 'Percentage of missed calls'),
            ('ticket_resolution_rate', 'Ticket Resolution Rate', 'percent', 'global', None,
             'tickets_closed / tickets_opened * 100', 2, 'Percentage of tickets resolved'),
            ('avg_deal_value', 'Avg Deal Value', 'currency', 'team', 'Sales',
             'revenue / deals_closed', 2, 'Average value per deal'),
        ]
        
        for key, name, unit, scope, team_name, formula, layer, desc in derived_metrics:
            metric = MetricDefinition.query.filter_by(key=key).first()
            if not metric:
                team_id = teams[team_name].id if team_name else None
                metric = MetricDefinition(
                    key=key,
                    display_name=name,
                    unit=unit,
                    scope=scope,
                    team_id=team_id,
                    is_derived=True,
                    formula=formula,
                    layer=layer,
                    description=desc,
                    active=True
                )
                db.session.add(metric)
                click.echo(f'  Created derived metric: {key}')
        
        db.session.commit()
        
        # Create reporting periods
        today = date.today()
        periods_data = []
        
        # Last 4 weeks
        for i in range(4):
            start = today - timedelta(days=today.weekday() + 7 * (i + 1))
            end = start + timedelta(days=6)
            year, week, _ = start.isocalendar()
            label = f'{year}-W{week:02d}'
            periods_data.append(('weekly', start, end, label))
        
        for period_type, start, end, label in periods_data:
            period = ReportingPeriod.query.filter_by(label=label).first()
            if not period:
                period = ReportingPeriod(
                    period_type=period_type,
                    start_date=start,
                    end_date=end,
                    label=label
                )
                db.session.add(period)
                click.echo(f'  Created period: {label}')
        
        db.session.commit()
        
        # Add sample metric values for the most recent period
        periods = ReportingPeriod.query.order_by(ReportingPeriod.start_date.desc()).limit(2).all()
        
        if periods:
            sample_values = {
                'Experience': {
                    'total_calls': [150, 180],
                    'missed_calls': [12, 8],
                    'tickets_opened': [45, 52],
                    'tickets_closed': [40, 48],
                    'hours_worked': [9600, 10080],
                },
                'Sales': {
                    'total_calls': [80, 95],
                    'missed_calls': [5, 3],
                    'revenue': [125000, 145000],
                    'deals_closed': [8, 12],
                    'hours_worked': [10800, 10500],
                },
                'Estimation': {
                    'total_calls': [20, 15],
                    'missed_calls': [2, 1],
                    'bugs_fixed': [25, 32],
                    'features_shipped': [3, 4],
                    'hours_worked': [12000, 12600],
                },
            }
            
            for team_name, metrics in sample_values.items():
                team = teams[team_name]
                for metric_key, values in metrics.items():
                    metric = MetricDefinition.query.filter_by(key=metric_key).first()
                    if metric:
                        for i, period in enumerate(periods):
                            if i < len(values):
                                existing = MetricValue.query.filter_by(
                                    metric_id=metric.id,
                                    team_id=team.id,
                                    reporting_period_id=period.id
                                ).first()
                                
                                if not existing:
                                    mv = MetricValue(
                                        metric_id=metric.id,
                                        team_id=team.id,
                                        reporting_period_id=period.id,
                                        value=values[i]
                                    )
                                    db.session.add(mv)
            
            db.session.commit()
            click.echo('  Added sample metric values')
        
        click.echo('\nDatabase seeding completed!')
        click.echo('\nSample login credentials:')
        click.echo('  Admin:      admin / admin123')
        click.echo('  Experience:    ahmedtamer / 1234')
        click.echo('  Sales:      richardgomez / 12345')
        click.echo('  Estimation: mujtaba / 123456')


@cli.command()
def init_db():
    """Initialize the database (create all tables)."""
    with app.app_context():
        db.create_all()
        click.echo('Database tables created.')


@cli.command()
def drop_db():
    """Drop all database tables."""
    if click.confirm('Are you sure you want to drop all tables?'):
        with app.app_context():
            db.drop_all()
            click.echo('All tables dropped.')


if __name__ == '__main__':
    cli()
