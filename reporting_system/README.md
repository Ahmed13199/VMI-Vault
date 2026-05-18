# Internal Reporting System

A Flask-based internal reporting system for Support, Sales, and Engineering teams to collect weekly/monthly KPI inputs, configure derived metrics via formulas, and display dashboards.

## Features

- **User Authentication**: Secure login with password hashing (Werkzeug)
- **Team Management**: Support, Sales, and Engineering teams
- **Rank-Based Access Control**: Admin, Team Leader, Senior, and Agent permissions with per-page view/edit control
- **User Management**: Admin-only user creation from Settings with password hashing, team assignment, and rank selection
- **Metric Definitions**: 
  - Layer 1: Base input metrics (e.g., total_calls, missed_calls)
  - Layer 2+: Derived metrics with formulas (e.g., missed_calls_pct = missed_calls / total_calls * 100)
- **Data Entry**: Input layer 1 metrics for reporting periods
- **Dashboard**: View KPI overview with calculated derived metrics
- **Formula Engine**: Safe evaluation of metric formulas

## Tech Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy ORM, PostgreSQL
- **Frontend**: Jinja2 templates, HTML5, CSS3, Vanilla JavaScript
- **Authentication**: Flask-Login with session-based authentication

## Project Structure

```
reporting_system/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py             # Configuration classes
│   ├── extensions.py         # Flask extensions
│   ├── models/               # Database models
│   │   ├── user.py
│   │   ├── team.py
│   │   └── metric.py
│   ├── services/             # Business logic
│   │   ├── auth_service.py
│   │   ├── metrics_service.py
│   │   └── formula_service.py
│   ├── blueprints/           # Route handlers
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── settings/
│   │   └── reporting/
│   ├── templates/            # Jinja2 templates
│   └── static/               # CSS, JS files
├── wsgi.py                   # WSGI entry point
├── manage.py                 # CLI management commands
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd reporting_system
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and secret key
   ```

5. **Create the database**:
   ```bash
   # In PostgreSQL:
   CREATE DATABASE reporting_system;
   ```

6. **Initialize database tables**:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

   Or use the management command:
   ```bash
   python manage.py init_db
   ```

7. **Seed sample data** (optional):
   ```bash
   python manage.py seed
   ```

### Running the Application

**Development**:
```bash
python wsgi.py
```
or
```bash
flask run
```

**Production** (with Gunicorn):
```bash
gunicorn wsgi:app
```

The application will be available at `http://localhost:5000`

## Default Credentials (after seeding)

| Username      | Password      | Role        | Rank         | Team        |
|---------------|---------------|-------------|--------------|-------------|
| admin         | admin123      | admin       | admin        | -           |
| ahmedtamer    | 1234          | experience  | agent        | Experience  |
| richardgomez  | 12345         | sales       | senior       | Sales       |
| mujtaba       | 123456        | estimation  | team_leader  | Estimation  |

## Management Commands

```bash
# Create a new user
python manage.py create_user

# List all users
python manage.py list_users

# Seed database with sample data
python manage.py seed

# Initialize database tables
python manage.py init_db

# Drop all tables (use with caution)
python manage.py drop_db
```

## URL Routes

| Route              | Description                    |
|--------------------|--------------------------------|
| `/auth/login`      | Login page                     |
| `/auth/logout`     | Logout                         |
| `/dashboard`       | Main dashboard with KPI cards  |
| `/settings`        | Metric definitions management  |
| `/settings/access-control` | Admin-only rank permission management |
| `/settings/users/new` | Admin-only user creation endpoint |
| `/reporting/input` | Data entry for base metrics    |
| `/reporting/output`| View all metrics for a period  |

## Formula Engine

The formula engine supports:
- Metric key references (e.g., `total_calls`, `missed_calls`)
- Numeric constants
- Arithmetic operators: `+`, `-`, `*`, `/`
- Parentheses for grouping

Example formulas:
- `missed_calls / total_calls * 100`
- `(tickets_closed / tickets_opened) * 100`
- `revenue / deals_closed`

The engine safely evaluates formulas without using Python's `eval()`.

## Extending the System

### Adding New Metrics

1. Go to **Settings** → **New Metric**
2. For base metrics: Set `is_derived` to False, layer = 1
3. For derived metrics: Set `is_derived` to True, provide formula, layer ≥ 2

### Access Model

The system now separates identity from authority:

- `role`: Department or functional identity such as `experience`, `sales`, `estimation`, or `admin`
- `rank`: Permission level such as `agent`, `senior`, `team_leader`, or `admin`
- `first_name` and `last_name`: User identity fields used by admin-created accounts
- Page permissions are stored in `access_permissions`
- Admins manage page visibility, edit rights, and user creation from **Settings**

### Adding New Core Pages Or Concepts

If you add a new core page, module, navigation item, or major concept that users can open or modify, you must wire it into the access-control system before considering the feature complete.

Required steps:

1. Add the page definition in `app/services/access_service.py`
2. Add route protection with `require_page_permission(...)`
3. Update navigation and UI visibility checks so unauthorized users do not see the entry point
4. Add the new page to the admin Access Control screen
5. Seed or migrate the corresponding `access_permissions` rows
6. If the page supports changes, distinguish between `view` and `edit` access

Rule:
- No new core item should be added without a permissions entry in Settings
- If a new feature can be viewed or edited, admins must be able to control that behavior from the Access Control page

## License

Internal use only.
