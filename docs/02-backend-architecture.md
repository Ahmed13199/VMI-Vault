# Backend Architecture

## Application Factory

Entry point:

```text
reporting_system/app/__init__.py
```

`create_app(config_name='default')` creates the Flask app, loads config,
initializes extensions, registers blueprints, and injects global template data.

Registered blueprints:

```text
/auth              auth
/dashboard         dashboard
/team-processes    team_processes
/documents         documents
/framework         framework
/journal           journal
/experience-team   experience_team
/sales-team        sales_team
/settings          settings
/reporting         reporting
```

Root `/` redirects to `dashboard.index`.

## Config

File:

```text
reporting_system/app/config.py
```

Important environment variables:

```text
SECRET_KEY
DATABASE_URL
TEST_DATABASE_URL
SQLALCHEMY_ECHO
R2_ACCOUNT_ID
R2_ENDPOINT_URL / R2_ENDPOINT
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_REGION
R2_BUCKET_NAME
R2_PUBLIC_URL_BASE
```

Default database URL:

```text
postgresql://postgres:postgres@localhost:5432/reporting_system
```

## Extensions

File:

```text
reporting_system/app/extensions.py
```

The app uses:

- `db`: SQLAlchemy ORM
- `migrate`: Flask-Migrate/Alembic
- `login_manager`: Flask-Login

## Authentication

Files:

```text
app/models/user.py
app/services/auth_service.py
app/blueprints/auth/routes.py
```

User password behavior:

- `User.set_password()` uses `werkzeug.security.generate_password_hash`.
- `User.check_password()` uses `check_password_hash`.

Django migration notes:

- You can map users into Django's `AbstractUser` or create a custom user model.
- Existing Werkzeug password hashes are not native Django hashes. Options:
  - Force password reset after migration.
  - Implement a custom Django password hasher that verifies Werkzeug hashes and
    upgrades them on successful login.
  - During migration, create unusable passwords and require resets.

## Authorization

Files:

```text
app/models/access_permission.py
app/services/access_service.py
app/permissions.py
```

The app protects routes with:

```python
@require_page_permission('page_key')
@require_page_permission('page_key', 'edit')
```

`AccessService.PAGE_DEFINITIONS` is the source of truth for page keys, labels,
routes, groups, and descriptions.

Permission behavior:

- Admin users always pass.
- Non-admin users use `effective_rank()`.
- If no DB row exists, `AccessService.default_permission()` is used.
- Admin-only conceptual pages:
  - `permissions`
  - `user_management`
  - `team_management`
- Editable pages by default:
  - `team_processes`
  - `documents`
  - `experience_team`
  - `sales_team`
  - `settings`
  - `reporting_input`
  - `journal`

Django migration notes:

- Create an `AccessPermission` model with unique `(page_key, rank)`.
- Implement a decorator or mixin equivalent to `require_page_permission`.
- Add a context processor for nav visibility, equivalent to
  `current_user.can_access_page(...)`.
- Seed defaults with a Django data migration or management command.

## Services

### MetricsService

File:

```text
app/services/metrics_service.py
```

Responsibilities:

- Determine teams/metrics visible to a user.
- Create/update/delete metric definitions.
- Manage metric categories and sub-categories.
- Manage reporting periods.
- Save metric values and targets.
- Generate weekly periods.
- Soft delete and hard delete metrics with safety checks.

Important methods:

```text
get_all_teams_for_user(user)
get_all_metrics_for_user(user, include_inactive=False)
create_metric(...)
update_metric(metric_id, **kwargs)
delete_metric(metric_id)
delete_metric_permanently(metric_id)
get_base_metrics_for_team(team_id)
get_derived_metrics_for_team(team_id)
save_metric_value_with_target(...)
get_metric_values(...)
get_metric_values_with_targets(...)
ensure_weekly_periods_for_current_year(start_week=40)
```

### FormulaService

File:

```text
app/services/formula_service.py
```

Responsibilities:

- Validate formula syntax.
- Extract metric keys referenced in a formula.
- Safely evaluate formulas without raw `eval`.
- Compute derived metrics in layer order.
- Format values for display.

Allowed formula features:

- Metric key references.
- Numeric constants.
- Arithmetic operators: `+`, `-`, `*`, `/`.
- Parentheses.
- Unary plus/minus.

Rejected formula features:

- Function calls.
- Attributes.
- Non-numeric constants.
- Unknown identifiers at evaluation time.

Django migration note:

This service is framework-independent enough to copy almost directly into a
Django service module.

### AccessService

File:

```text
app/services/access_service.py
```

Responsibilities:

- Define page registry.
- Seed default permission rows.
- Calculate a permission matrix for the admin UI.
- Save access-control form data.
- Determine first accessible route after login.
- Enforce view/edit permissions.

### R2Service

File:

```text
app/services/r2_service.py
```

Responsibilities:

- Build an S3-compatible boto3 client for Cloudflare R2.
- Upload file objects.
- Delete objects.
- Generate presigned read URLs.
- Optionally build public URLs.

Django migration options:

- Keep this service mostly unchanged and call it from views.
- Or use `django-storages` with an S3-compatible backend configured for R2.

## Error/Message Model

The Flask app uses `flash(message, category)` for user feedback. Django
equivalent is `django.contrib.messages`.

Common categories:

```text
success
error
info
```

## Transaction Style

Current code uses `db.session.add(...)`, `db.session.delete(...)`, and
`db.session.commit()` directly in routes/services.

Django migration recommendations:

- Use `transaction.atomic()` for multi-step writes such as:
  - document upload DB write after R2 upload
  - folder recursive delete
  - journal table creation
  - reporting value batch save
  - sales guideline resource creation
- Keep business logic in service modules to avoid fat Django views.

